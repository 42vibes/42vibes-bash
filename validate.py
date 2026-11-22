#!/usr/bin/env python3
"""Validate the generated 42vibes shell/tool profiles.

Runs structural checks plus the tools that are available on this machine:

* starship.toml            -- tomllib (Python 3.11+)
* bat/42vibes.tmTheme     -- xml.etree.ElementTree
* bat/42vibes-light.tmTheme -- xml.etree + Kontrastprüfung
* palette.sh               -- sh -n and bash -n
* dircolors.gnu            -- dircolors -b (if dircolors is installed)
* ls --color=always        -- end-to-end: control sequences instead of SGR digits
* delta.gitconfig          -- git config -f ... --list
* lscolors.bsd             -- LSCOLORS length/alphabet check (11 pairs)
* preview/palette-*.svg    -- SVG/XML, alle semantic- und ANSI-Hex-Werte
* README.md/README.de.md   -- Sprachumschalter, Pflichtthemen, Bilder, Lizenz
* build.py --check         -- generated files are up to date (deterministic)

Exit code 0 means all checks passed, 1 means at least one failed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent

HEX = re.compile(r"^#[0-9a-f]{6}$", re.I)
SCOPE_LIST = re.compile(r"\]\(([^)]*)\)")
EXPORT_LSCOLORS = re.compile(r'LSCOLORS="([^"]+)"')
STYLE_SUFFIX = ("style", "_style")

# dircolors.gnu: plain values are SGR numbers, these four are control sequences.
SGR_VALUE = re.compile(r"[0-9]+(?:;[0-9]+)*")
CONTROL_KEYS = ("LEFTCODE", "RIGHTCODE", "ENDCODE", "CLRTOEOL")
LEGACY_CONTROL_ALIASES = ("LEFT", "RIGHT", "END")
ESCAPE_START = re.compile(r"\\(?:e|E|033|x1b|X1B)\[")
# ls writes ESC [ params letter (and ESC [ K); anything else is broken output.
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ESCAPE_ANY = re.compile(r"\x1b(?!\[[0-9;]*[A-Za-z])")
BAD_VISIBLE = re.compile(r"[0-9;]")

SVG_NS = "http://www.w3.org/2000/svg"
SEMANTIC_TOKENS = [
    "bg", "bg_deep", "surface", "surface_high", "surface_max", "text",
    "text_muted", "text_faint", "accent", "interactive", "warm", "border",
    "success", "warning", "error", "info",
]
ANSI_TOKENS = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]


def luminance(value: str) -> float:
    raw = value.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)

# Starship built-ins and style modifiers that never refer to a palette entry.
STYLE_MODIFIERS = {
    "bold", "dimmed", "italic", "underline", "blink", "reverse", "reversed",
    "hidden", "strikethrough", "none", "plain",
}
BUILTIN_COLORS = {
    "black", "red", "green", "yellow", "blue", "purple", "magenta", "cyan",
    "white", "bright-black", "bright-red", "bright-green", "bright-yellow",
    "bright-blue", "bright-purple", "bright-magenta", "bright-cyan",
    "bright-white",
}
REQUIRED_SCOPES = {
    "comment", "keyword", "string", "constant.numeric", "function", "type",
    "variable", "constant", "markup.heading", "markup.bold", "markup.strong",
    "markup.link", "invalid",
}
REQUIRED_FILES = [
    "starship.toml",
    "dircolors.gnu",
    "lscolors.bsd",
    "bat/42vibes.tmTheme",
    "bat/42vibes-light.tmTheme",
    "delta.gitconfig",
    "palette.sh",
    "preview/palette-dark.svg",
    "preview/palette-light.svg",
    "README.md",
    "README.de.md",
    "LICENSE",
    "vendor/palette.json",
]

README_REQUIREMENTS = {
    "README.md": {
        "switcher": "**English** · [Deutsch](README.de.md)",
        "preview_note": "Generated palette preview",
        "license": "## License",
        "required": [
            "terminal profile first",
            "11 pairs",
            "bash 3.2",
            "Truecolor",
            "dircolors",
            "LEFTCODE",
            "LSCOLORS",
            "delta",
            "Nerd Font",
        ],
    },
    "README.de.md": {
        "switcher": "[English](README.md) · **Deutsch**",
        "preview_note": "Generierte Palettenvorschau",
        "license": "## Lizenz",
        "required": [
            "Terminal-Profil zuerst",
            "11 Paare",
            "bash 3.2",
            "Truecolor",
            "dircolors",
            "LEFTCODE",
            "LSCOLORS",
            "delta",
            "Nerd-Font",
        ],
    },
}

# delta: 8 ANSI names plus bright forms without a hyphen, style attributes and
# the special style words. Hex would also be valid, but this repo uses ANSI.
DELTA_COLORS = {
    "black", "red", "green", "yellow", "blue", "magenta", "purple", "cyan",
    "white", "brightblack", "brightred", "brightgreen", "brightyellow",
    "brightblue", "brightmagenta", "brightcyan", "brightwhite",
}
DELTA_ATTRIBUTES = {
    "blink", "bold", "dim", "hidden", "italic", "reverse", "strike", "ul",
    "underline", "box", "ol", "omit", "none",
}
DELTA_SPECIAL = {"auto", "normal", "raw", "syntax"}


class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def ok(message: str) -> None:
    print(f"[ok] {message}")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )


# ---------------------------------------------------------------------------
# starship.toml
# ---------------------------------------------------------------------------


def check_style(path: str, spec: str, palette: dict) -> None:
    for token in spec.split():
        if token in STYLE_MODIFIERS or token.startswith("$"):
            continue
        color = token
        if token.startswith(("fg:", "bg:")):
            color = token.split(":", 1)[1]
        if color in palette or color in BUILTIN_COLORS:
            continue
        fail(f"starship.toml: {path} verweist auf unbekannte Farbe {color!r} ({spec!r})")


def walk_starship(node, trail: str, palette: dict) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            walk_starship(value, f"{trail}.{key}" if trail else key, palette)
        return
    if isinstance(node, list):
        for index, value in enumerate(node):
            walk_starship(value, f"{trail}[{index}]", palette)
        return
    if not isinstance(node, str):
        return
    key = trail.rsplit(".", 1)[-1]
    if key.endswith(STYLE_SUFFIX):
        check_style(trail, node, palette)
    for spec in SCOPE_LIST.findall(node):
        check_style(trail, spec, palette)


def validate_starship() -> None:
    path = ROOT / "starship.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    palettes = data.get("palettes")
    if not isinstance(palettes, dict):
        fail("starship.toml: [palettes] fehlt")
    active = data.get("palette")
    if not isinstance(active, str) or active not in palettes:
        fail(f"starship.toml: palette={active!r} existiert nicht in [palettes]")
    for name in ("42vibes", "42vibes_light"):
        if not isinstance(palettes.get(name), dict):
            fail(f"starship.toml: [palettes.{name}] fehlt")
    for name, colors in palettes.items():
        for color_name, value in colors.items():
            if not isinstance(value, str) or not HEX.match(value):
                fail(f"starship.toml: palettes.{name}.{color_name} ist kein Hex: {value!r}")
            if color_name in BUILTIN_COLORS:
                fail(f"starship.toml: palettes.{name}.{color_name} überschattet eine Built-in-Farbe")
    walk_starship(data, "", palettes[active])
    prompt_format = data.get("format")
    if not isinstance(prompt_format, str):
        fail("starship.toml: globales format fehlt")
    required_modules = (
        "$status", "$character", "$username", "$hostname", "$directory",
        "$git_branch", "$git_status", "$python", "$nodejs", "$rust",
        "$golang", "$terraform",
    )
    missing = [module for module in required_modules if module not in prompt_format]
    if missing:
        fail(f"starship.toml: globales format lässt Module weg: {', '.join(missing)}")
    directory = data.get("directory")
    if not isinstance(directory, dict) or directory.get("truncation_symbol") != "…/":
        fail("starship.toml: directory.truncation_symbol muss reines '…/' sein")
    status = data.get("status")
    if not isinstance(status, dict) or status.get("disabled") is not False:
        fail("starship.toml: status muss disabled = false sein")
    if status.get("success_symbol") != "":
        fail("starship.toml: status.success_symbol muss leer sein (nur Fehler zeigen)")
    ok(f"starship.toml (tomllib, Palette {active!r}, {len(palettes[active])} Farben)")


# ---------------------------------------------------------------------------
# bat/42vibes.tmTheme
# ---------------------------------------------------------------------------


def plist_pairs(node: ET.Element) -> dict[str, ET.Element]:
    children = list(node)
    if len(children) % 2:
        fail(f"tmTheme: {node.tag} hat eine ungerade Anzahl Kinder")
    result: dict[str, ET.Element] = {}
    for index in range(0, len(children), 2):
        key, value = children[index], children[index + 1]
        if key.tag != "key":
            fail(f"tmTheme: erwartet <key>, gefunden <{key.tag}>")
        result[key.text or ""] = value
    return result


def validate_tmtheme(relative: str, expected_name: str) -> None:
    path = ROOT / relative
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        fail(f"{relative}: XML nicht parsebar: {error}")
    if root.tag != "plist" or root.get("version") != "1.0":
        fail(f"{relative}: Wurzel muss <plist version=\"1.0\"> sein")
    top = plist_pairs(root.find("dict"))
    if top.get("name") is None or top["name"].text != expected_name:
        fail(f"{relative}: name muss {expected_name!r} sein")
    if top.get("semanticClass") is None or top["semanticClass"].text != f"theme.{expected_name}":
        fail(f"{relative}: semanticClass muss 'theme.{expected_name}' sein")
    settings = top.get("settings")
    if settings is None or settings.tag != "array":
        fail(f"{relative}: settings-Array fehlt")

    entries = list(settings)
    if len(entries) < 20:
        fail(f"{relative}: zu wenige Scope-Einträge ({len(entries)})")

    global_entry = plist_pairs(entries[0])
    if "scope" in global_entry:
        fail(f"{relative}: erster Eintrag darf keinen scope haben")
    global_settings = plist_pairs(global_entry["settings"])
    for required in ("background", "foreground"):
        if required not in global_settings:
            fail(f"{relative}: globale Einstellung {required} fehlt")
    for key, node in global_settings.items():
        if not HEX.match(node.text or ""):
            fail(f"{relative}: globale Farbe {key} ist kein Hex: {node.text!r}")

    global_bg = global_settings["background"].text or ""
    ratios: list[float] = []

    def check(label: str, foreground: str, background: str, minimum: float) -> None:
        ratio = contrast(foreground, background)
        ratios.append(ratio)
        if ratio < minimum:
            fail(
                f"{relative}: {label} hat nur {ratio:.2f}:1 "
                f"({foreground} auf {background}, min {minimum:.1f}:1)"
            )

    check("foreground/background", global_settings["foreground"].text or "", global_bg, 10.0)
    check(
        "selectionForeground/selection",
        global_settings["selectionForeground"].text or "",
        global_settings["selection"].text or "",
        4.5,
    )
    check(
        "findHighlightForeground/findHighlight",
        global_settings["findHighlightForeground"].text or "",
        global_settings["findHighlight"].text or "",
        4.5,
    )
    check("invisibles/background", global_settings["invisibles"].text or "", global_bg, 3.0)
    check("caret/background", global_settings["caret"].text or "", global_bg, 3.0)
    check(
        "gutterForeground/gutter",
        global_settings["gutterForeground"].text or "",
        global_settings["gutter"].text or "",
        3.0,
    )

    found: set[str] = set()
    for entry in entries[1:]:
        data = plist_pairs(entry)
        scope = data.get("scope")
        inner = data.get("settings")
        if scope is None or inner is None:
            fail(f"{relative}: Scope-Eintrag ohne scope/settings")
        tokens = {part.strip() for part in (scope.text or "").split(",")}
        found |= tokens
        inner_data = plist_pairs(inner)
        for key in ("foreground", "background"):
            if key in inner_data and not HEX.match(inner_data[key].text or ""):
                fail(f"{relative}: {scope.text}: {key} ist kein Hex")
        if "fontStyle" in inner_data:
            styles = set((inner_data["fontStyle"].text or "").split())
            if not styles <= {"bold", "italic", "underline", "strikethrough"}:
                fail(f"{relative}: {scope.text}: ungültiger fontStyle {styles}")

        if "foreground" not in inner_data:
            fail(f"{relative}: {scope.text}: foreground fehlt")
        scope_bg = (inner_data.get("background").text if inner_data.get("background") is not None else global_bg) or ""
        check(scope.text or "", inner_data["foreground"].text or "", scope_bg, 4.5)

    missing = REQUIRED_SCOPES - found
    if missing:
        fail(f"{relative}: Pflicht-Scopes fehlen: {sorted(missing)}")
    ok(
        f"{relative} (xml.etree, {len(entries)} Einträge, {len(found)} Scopes, "
        f"min. Kontrast {min(ratios):.2f}:1)"
    )


# ---------------------------------------------------------------------------
# palette.sh
# ---------------------------------------------------------------------------


def validate_palette_sh() -> None:
    path = ROOT / "palette.sh"
    text = path.read_text(encoding="utf-8")

    for banned in ("declare ", "typeset ", "[[", "=(", "local "):
        if banned in text:
            fail(f"palette.sh: bash-spezifisches Konstrukt gefunden: {banned!r}")

    if "export VIBES_BG" not in text or "export C_BG" not in text:
        fail("palette.sh: erwartete VIBES_*/C_*-Exporte fehlen")
    for name in ("VIBES_BG", "VIBES_LIGHT_BG", "VIBES_ANSI_RED", "C_ACCENT"):
        if f"{name}=" not in text:
            fail(f"palette.sh: Variable {name} fehlt")

    for shell in ("sh", "bash"):
        binary = shutil.which(shell)
        if binary is None:
            fail(f"palette.sh: {shell} nicht im PATH")
        result = run([binary, "-n", "palette.sh"])
        if result.returncode != 0:
            fail(f"palette.sh: {shell} -n Exit {result.returncode}: {result.stderr.strip()}")
        ok(f"palette.sh: {shell} -n (Exit 0)")


# ---------------------------------------------------------------------------
# dircolors.gnu
# ---------------------------------------------------------------------------


def validate_dircolors() -> None:
    path = ROOT / "dircolors.gnu"
    text = path.read_text(encoding="utf-8")

    seen: set[str] = set()
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != 2:
            fail(f"dircolors.gnu: ungültige Zeile: {line!r}")
        key, value = parts
        if key in seen:
            fail(f"dircolors.gnu: doppelter Schlüssel {key}")
        seen.add(key)
        values[key] = value
        if key in CONTROL_KEYS:
            continue
        if not SGR_VALUE.fullmatch(value):
            fail(f"dircolors.gnu: ungültiger SGR-Wert für {key}: {value!r}")

    # Obsolete aliases would duplicate lc/rc/ec in LS_COLORS with a second,
    # possibly numeric value. Only the *CODE spellings are emitted.
    for alias in LEGACY_CONTROL_ALIASES:
        if alias in seen:
            fail(
                f"dircolors.gnu: veralteter Alias {alias} vorhanden; "
                f"nur {', '.join(CONTROL_KEYS)} verwenden"
            )

    for key in CONTROL_KEYS:
        if key not in values:
            fail(f"dircolors.gnu: Steuersequenz {key} fehlt")
        value = values[key]
        # ls writes these verbatim: a bare SGR number would appear as text.
        if SGR_VALUE.fullmatch(value):
            fail(
                f"dircolors.gnu: {key} ist eine SGR-Zahl ({value!r}); "
                "erwartet wird eine Steuersequenz wie \\e["
            )
        if key == "RIGHTCODE":
            # Terminator of lc+SGR+rc: "m" is correct, an escape sequence is
            # also accepted but must still not be a bare number.
            if value != "m" and not ESCAPE_START.search(value):
                fail(
                    f"dircolors.gnu: RIGHTCODE muss 'm' (SGR-Terminator) oder "
                    f"eine Escape-Sequenz sein, nicht {value!r}"
                )
        elif not ESCAPE_START.search(value):
            fail(
                f"dircolors.gnu: {key} enthält keine Escape-Sequenz "
                f"(\\e[ bzw. \\033[): {value!r}"
            )

    for required in ("NORMAL", "DIR", "LINK", "EXEC", "ORPHAN", "MISSING", ".diff", ".patch"):
        if required not in seen:
            fail(f"dircolors.gnu: Pflichtschlüssel {required} fehlt")

    binary = shutil.which("dircolors")
    if binary is None:
        ok("dircolors.gnu (statisch; dircolors nicht installiert, -b übersprungen)")
        return
    result = run([binary, "-b", "dircolors.gnu"])
    if result.returncode != 0:
        fail(f"dircolors -b Exit {result.returncode}: {result.stderr.strip()}")
    if "LS_COLORS=" not in result.stdout:
        fail("dircolors -b lieferte kein LS_COLORS")
    for needle in ("di=01;34", "*.diff=01;33", "*.patch=01;36"):
        if needle not in result.stdout:
            fail(f"dircolors-Ausgabe enthält {needle!r} nicht")
    # The control sequences must survive as escapes, exactly once each.
    for needle in ("lc=\\e[", "rc=m", "ec=\\e[0m", "cl=\\e[K"):
        if needle not in result.stdout:
            fail(f"dircolors-Ausgabe enthält {needle!r} nicht")
    assignment = re.search(r"LS_COLORS='([^']*)'", result.stdout)
    if assignment is None:
        fail("dircolors -b: LS_COLORS-Zuweisung nicht lesbar")
    indicators: dict[str, list[str]] = {}
    for entry in assignment.group(1).split(":"):
        key, _, value = entry.partition("=")
        indicators.setdefault(key, []).append(value)
    for key in ("lc", "rc", "ec", "cl"):
        found = indicators.get(key, [])
        if len(found) != 1:
            fail(f"dircolors-Ausgabe enthält {key}= {len(found)}x (erwartet: 1x)")
        if SGR_VALUE.fullmatch(found[0]):
            fail(f"dircolors-Ausgabe enthält numerische Steuersequenz {key}={found[0]}")
    ok(f"dircolors.gnu: dircolors -b (Exit 0, {len(seen)} Schlüssel)")


# End-to-end check: the reported bug produced output such as
# "0001;3401;3301;34name00" instead of escape sequences.
LS_FIXTURE_NAMES = [
    "subdir",
    "runme",
    "link",
    "change.diff",
    "change.patch",
    "archive.tar.gz",
    "notes.md",
]


def build_ls_fixture(root: Path) -> None:
    (root / "subdir").mkdir()
    executable = root / "runme"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    (root / "link").symlink_to("subdir")
    for name in ("change.diff", "change.patch", "archive.tar.gz", "notes.md"):
        (root / name).write_text("x\n", encoding="utf-8")


def validate_ls_output() -> None:
    ls_binary = shutil.which("ls")
    dircolors_binary = shutil.which("dircolors")
    shell = shutil.which("bash") or shutil.which("sh")
    if ls_binary is None or dircolors_binary is None or shell is None:
        ok("ls --color=always (übersprungen: ls, dircolors oder Shell fehlt)")
        return

    with tempfile.TemporaryDirectory(prefix="42vibes-ls-") as temporary:
        root = Path(temporary)
        build_ls_fixture(root)
        script = 'eval "$(dircolors -b "$1")" || exit 1; shift; ls --color=always -d "$@"'
        result = subprocess.run(
            [shell, "-c", script, "sh", str(ROOT / "dircolors.gnu"), *LS_FIXTURE_NAMES],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        if result.returncode != 0:
            fail(
                f"ls --color=always Exit {result.returncode}: "
                f"{(result.stderr or result.stdout).strip()}"
            )

        output = result.stdout
        if not output:
            fail("ls --color=always lieferte keine Ausgabe")

        # After removing valid escapes only the file names may remain: any
        # digit or ';' is the reported bug (literal "0001;34..." text).
        visible_text = ANSI_ESCAPE.sub("", output)
        if BAD_VISIBLE.search(visible_text):
            fail(
                "ls --color=always: wörtliche SGR-Ziffern in der Ausgabe "
                f"(erste Zeile {visible_text.splitlines()[0]!r})"
            )
        if "\x1b[" not in output:
            fail("ls --color=always: keine Escape-Sequenzen in der Ausgabe")
        if ESCAPE_ANY.search(output):
            fail("ls --color=always: unerwartete/unvollständige Escape-Sequenz")

        visible = [line.strip() for line in visible_text.splitlines()]
        if sorted(visible) != sorted(LS_FIXTURE_NAMES):
            fail(
                "ls --color=always: sichtbarer Text ist nicht genau die "
                f"Dateiliste: {visible!r}"
            )
        for sgr in ("\x1b[01;33m", "\x1b[01;36m", "\x1b[01;31m", "\x1b[01;34m"):
            if sgr not in output:
                fail(f"ls --color=always: erwartete Sequenz {sgr!r} fehlt")
    ok("ls --color=always: Steuersequenzen statt SGR-Ziffern (End-to-End)")


# ---------------------------------------------------------------------------
# lscolors.bsd
# ---------------------------------------------------------------------------


def validate_lscolors() -> None:
    path = ROOT / "lscolors.bsd"
    text = path.read_text(encoding="utf-8")
    if "CLICOLOR=1" not in text:
        fail("lscolors.bsd: CLICOLOR=1 fehlt")
    match = EXPORT_LSCOLORS.search(text)
    if not match:
        fail("lscolors.bsd: export LSCOLORS=... fehlt")
    value = match.group(1)
    if len(value) != 22:
        fail(f"lscolors.bsd: LSCOLORS hat {len(value)} Zeichen, macOS erwartet 22 (11 Paare)")
    if not re.fullmatch(r"[a-hA-Hx]{22}", value):
        fail(f"lscolors.bsd: ungültige LSCOLORS-Zeichen: {value!r}")
    ok(f"lscolors.bsd (LSCOLORS, 11 Paare, {value!r})")


# ---------------------------------------------------------------------------
# delta.gitconfig
# ---------------------------------------------------------------------------


def validate_delta() -> None:
    binary = shutil.which("git")
    if binary is None:
        fail("delta.gitconfig: git nicht im PATH")
    result = run([binary, "config", "-f", "delta.gitconfig", "--list"])
    if result.returncode != 0:
        fail(f"git config -f delta.gitconfig Exit {result.returncode}: {result.stderr.strip()}")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.lower()] = value
    required = {
        "core.pager": "delta",
        "interactive.difffilter": "delta --color-only",
        "delta.features": "42vibes",
        "delta.syntax-theme": "42vibes",
        "delta.42vibes.minus-style": "red",
        "delta.42vibes.plus-style": "green",
        "delta.42vibes.file-style": "bold blue",
        "delta.42vibes.hunk-header-style": "bold yellow",
        "delta.42vibes-light.light": "true",
        "delta.42vibes-light.minus-style": "red",
        "delta.42vibes-light.plus-style": "green",
        "delta.42vibes-light.file-style": "bold blue",
        "delta.42vibes-light.hunk-header-style": "bold yellow",
    }
    for key, expected in required.items():
        if values.get(key) != expected:
            fail(f"delta.gitconfig: {key}={values.get(key)!r}, erwartet {expected!r}")
    if values.get("delta.dark") == "true" and values.get("delta.light") == "true":
        fail("delta.gitconfig: dark und light dürfen nicht beide gesetzt sein")
    for key, value in values.items():
        if not key.startswith(("delta.42vibes.", "delta.42vibes-light.")):
            continue
        if not key.endswith("-style"):
            continue
        for token in value.split():
            if token in DELTA_ATTRIBUTES or token in DELTA_SPECIAL or token in DELTA_COLORS:
                continue
            fail(f"delta.gitconfig: {key} nutzt unbekannten Style-Token {token!r}")
    ok(f"delta.gitconfig (git config --list, {len(values)} Schlüssel)")


# ---------------------------------------------------------------------------
# preview/palette-*.svg
# ---------------------------------------------------------------------------


def validate_preview() -> None:
    palette = json.loads(
        (ROOT / "vendor" / "palette.json").read_text(encoding="utf-8")
    )
    readmes = {
        relative: (ROOT / relative).read_text(encoding="utf-8")
        for relative in README_REQUIREMENTS
    }

    for mode in ("dark", "light"):
        relative = f"preview/palette-{mode}.svg"
        path = ROOT / relative
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            fail(f"{relative}: XML nicht parsebar: {error}")
        if root.tag != f"{{{SVG_NS}}}svg":
            fail(f"{relative}: Wurzel muss <svg xmlns={SVG_NS!r}> sein")
        if "ui-monospace" not in (root.get("font-family") or ""):
            fail(f"{relative}: font-family 'ui-monospace, monospace' fehlt")
        if "ui-monospace, monospace" not in path.read_text(encoding="utf-8"):
            fail(f"{relative}: font-family-Angabe fehlt im SVG-Text")

        source = path.read_text(encoding="utf-8").lower()
        for name in SEMANTIC_TOKENS:
            value = palette[mode]["semantic"][name]
            if value.lower() not in source:
                fail(f"{relative}: semantischer Hex-Wert fehlt: {name}={value}")
            if name not in source:
                fail(f"{relative}: semantisches Label fehlt: {name}")
        for name in ANSI_TOKENS:
            value = palette[mode]["ansi"][name]
            if value.lower() not in source:
                fail(f"{relative}: ANSI-Hex-Wert fehlt: {name}={value}")
            if name not in source:
                fail(f"{relative}: ANSI-Label fehlt: {name}")

        for name, text in readmes.items():
            if relative not in text:
                fail(f"{name}: Bildpfad {relative!r} fehlt")

    ok("preview/palette-*.svg (XML, alle 16+16 Hex-Werte, README-Bildpfade)")


# ---------------------------------------------------------------------------
# README and build freshness
# ---------------------------------------------------------------------------


def validate_readme() -> None:
    for relative, spec in README_REQUIREMENTS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "{{" in text or "}}" in text:
            fail(f"{relative}: unersetzte Template-Platzhalter")
        if spec["switcher"] not in "\n".join(text.splitlines()[:5]):
            fail(f"{relative}: Sprachumschalter fehlt oder steht nicht oben")
        if spec["license"] not in text:
            fail(f"{relative}: Lizenzabschnitt {spec['license']!r} fehlt")
        for phrase in ("[`LICENSE`](LICENSE)", "MIT", "Copyright 2026 42vibes"):
            if phrase not in text:
                fail(f"{relative}: Lizenzverweis {phrase!r} fehlt")
        for phrase in spec["required"]:
            if phrase not in text:
                fail(f"{relative}: erwarteter Abschnitt/Stichwort fehlt: {phrase!r}")
        for mode in ("dark", "light"):
            if f"preview/palette-{mode}.svg" not in text:
                fail(f"{relative}: Bildpfad preview/palette-{mode}.svg fehlt")
        if spec["preview_note"] not in text:
            fail(f"{relative}: Vorschau nicht als generiert gekennzeichnet")
        ok(f"{relative} (Template ersetzt, Umschalter, Lizenz, Pflichtthemen)")


def validate_build_freshness() -> None:
    result = run([sys.executable, "build.py", "--check"])
    if result.returncode != 0:
        fail(
            "build.py --check: generierte Dateien sind nicht aktuell:\n"
            + (result.stdout + result.stderr).strip()
        )
    ok("build.py --check (generierte Dateien aktuell)")


BUILD_DIGEST_SCRIPT = r'''
import hashlib, importlib.util
spec = importlib.util.spec_from_file_location("build42", "build.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.collect()
digest = hashlib.sha256()
for path, content in module.ARTIFACTS:
    digest.update(str(path.relative_to(module.ROOT)).encode())
    digest.update(hashlib.sha256(content.encode()).digest())
print(digest.hexdigest())
'''


def build_digest() -> str:
    result = run([sys.executable, "-c", BUILD_DIGEST_SCRIPT])
    if result.returncode != 0:
        fail("build.py: Neuberechnung fehlgeschlagen:\n" + result.stderr.strip())
    return result.stdout.strip()


def validate_build_deterministic() -> None:
    first = build_digest()
    second = build_digest()
    if first != second:
        fail(f"build.py ist nicht deterministisch ({first} != {second})")
    ok(f"build.py deterministisch (sha256 {first[:12]}…)")


def main() -> int:
    try:
        for relative in REQUIRED_FILES:
            path = ROOT / relative
            if not path.is_file():
                fail(f"Datei fehlt: {relative}")
        validate_build_freshness()
        validate_build_deterministic()
        validate_starship()
        validate_tmtheme("bat/42vibes.tmTheme", "42vibes")
        validate_tmtheme("bat/42vibes-light.tmTheme", "42vibes-light")
        validate_palette_sh()
        validate_dircolors()
        validate_ls_output()
        validate_lscolors()
        validate_delta()
        validate_readme()
        validate_preview()
    except ValidationError as error:
        print(f"[FEHLER] {error}", file=sys.stderr)
        return 1
    print("validate.py: alle Prüfungen ok (Exit 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
