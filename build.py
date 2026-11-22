#!/usr/bin/env python3
"""Generate shell and tool profiles for the 42vibes palette.

Input: vendor/palette.json (copy of ../42vibes-palette/palette.json).
Output: starship.toml, dircolors.gnu, lscolors.bsd, bat/42vibes.tmTheme,
bat/42vibes-light.tmTheme, delta.gitconfig, palette.sh,
preview/palette-dark.svg, preview/palette-light.svg,
README.md (English) and README.de.md (German).

All outputs are checked in. Run ``python3 build.py`` after palette changes and
``python3 build.py --check`` to verify that the checked-in files are current.
"""

from __future__ import annotations

import json
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PALETTE = json.loads((ROOT / "vendor" / "palette.json").read_text(encoding="utf-8"))

MODES = ("dark", "light")
SEM = {mode: PALETTE[mode]["semantic"] for mode in MODES}
ANSI = {mode: PALETTE[mode]["ansi"] for mode in MODES}
HUES = {mode: PALETTE[mode]["hues"] for mode in MODES}

HEADER = "GENERIERT von build.py aus vendor/palette.json. Nicht direkt bearbeiten."

# ---------------------------------------------------------------------------
# HSL ramps -- identical to the other 42vibes targets (OpenCode theme etc.).
# ---------------------------------------------------------------------------

STEPS = ["100", "200", "300", "400", "500", "600", "700", "800", "900"]
DARK_OFFSETS = dict(
    zip(STEPS, [0.28, 0.16, 0.09, 0.04, 0.00, -0.10, -0.20, -0.30, -0.38])
)
LIGHT_OFFSETS = dict(
    zip(STEPS, [-0.30, -0.20, -0.12, -0.05, 0.00, 0.08, 0.15, 0.22, 0.28])
)
SATURATION_SCALE = 0.55


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def rgb_to_hsl(value: str) -> tuple[float, float, float]:
    r, g, b = (c / 255 for c in hex_to_rgb(value))
    high, low = max(r, g, b), min(r, g, b)
    light = (high + low) / 2
    if high == low:
        return 0.0, 0.0, light
    delta = high - low
    saturation = delta / (1 - abs(2 * light - 1))
    if high == r:
        hue = ((g - b) / delta) % 6
    elif high == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    return hue * 60, saturation, light


def hsl_to_hex(hue: float, saturation: float, light: float) -> str:
    light = max(0.0, min(1.0, light))
    saturation = max(0.0, min(1.0, saturation))
    chroma = (1 - abs(2 * light - 1)) * saturation
    x = chroma * (1 - abs((hue / 60) % 2 - 1))
    m = light - chroma / 2
    if hue < 60:
        r, g, b = chroma, x, 0
    elif hue < 120:
        r, g, b = x, chroma, 0
    elif hue < 180:
        r, g, b = 0, chroma, x
    elif hue < 240:
        r, g, b = 0, x, chroma
    elif hue < 300:
        r, g, b = x, 0, chroma
    else:
        r, g, b = chroma, 0, x
    return rgb_to_hex(((r + m) * 255, (g + m) * 255, (b + m) * 255))


def shift(anchor: str, offsets: dict[str, float]) -> dict[str, str]:
    """Move only HSL lightness; soften the ends of the ramp slightly."""
    hue, saturation, light = rgb_to_hsl(anchor)
    return {
        step: hsl_to_hex(
            hue,
            saturation * (SATURATION_SCALE if step in ("100", "900") else 1.0),
            light + offset,
        )
        for step, offset in offsets.items()
    }


DARK_RAMP = {name: shift(color, DARK_OFFSETS) for name, color in HUES["dark"].items()}
LIGHT_RAMP = {name: shift(color, LIGHT_OFFSETS) for name, color in HUES["light"].items()}


def dark(hue: str, step: str) -> str:
    return DARK_RAMP[hue][step]


# ---------------------------------------------------------------------------
# Artifact registry
# ---------------------------------------------------------------------------

ARTIFACTS: list[tuple[Path, str]] = []


def add(relative: str, content: str) -> None:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise SystemExit(f"build.py: Ausgabepfad ausserhalb des Repos: {path}")
    ARTIFACTS.append((path, content.rstrip() + "\n"))


# ---------------------------------------------------------------------------
# starship.toml
# ---------------------------------------------------------------------------


def starship_palette(mode: str) -> dict[str, str]:
    sem = SEM[mode]
    mapping = {
        "bg": sem["bg"],
        "bg_deep": sem["bg_deep"],
        "surface": sem["surface"],
        "surface_high": sem["surface_high"],
        "surface_max": sem["surface_max"],
        "text": sem["text"],
        "muted": sem["text_muted"],
        "faint": sem["text_faint"],
        "accent": sem["accent"],
        "interactive": sem["interactive"],
        "warm": sem["warm"],
        "border": sem["border"],
        "success": sem["success"],
        "warning": sem["warning"],
        "error": sem["error"],
        "info": sem["info"],
    }
    for name, value in ANSI[mode].items():
        mapping[f"ansi_{name}"] = value
    return mapping


def build_starship() -> str:
    lines = [
        f"# {HEADER}",
        '# Absichtlich keine Nerd-Font-Glyphen; siehe README ("Symbole").',
        '"$schema" = "https://starship.rs/config-schema.json"',
        'palette = "42vibes"',
        '# Heller Hintergrund? Dann die naechste Zeile aktivieren:',
        '# palette = "42vibes_light"',
        "add_newline = true",
        "",
        'format = """',
        "$status[╭─](muted) $username$hostname$directory$git_branch$git_status",
        "([│](muted) $python$nodejs$deno$bun$rust$golang$java$kotlin$ruby$php$elixir$haskell$lua$perl$swift$zig$dotnet$terraform$kubernetes$docker_context$aws$package$git_state$cmd_duration$jobs$shell$time)",
        "[╰─](muted)$character",
        '"""',
        "",
    ]

    for mode, name in (("dark", "42vibes"), ("light", "42vibes_light")):
        lines.append(f"[palettes.{name}]")
        for key, value in starship_palette(mode).items():
            lines.append(f'{key} = "{value}"')
        lines.append("")

    lines.append(
        textwrap.dedent(
            """\
            [character]
            format = "$symbol "
            success_symbol = "[❯](bold accent)"
            error_symbol = "[❯](bold error)"
            vimcmd_symbol = "[❮](bold interactive)"
            vimcmd_replace_one_symbol = "[❮](bold warm)"
            vimcmd_replace_symbol = "[❮](bold warm)"
            vimcmd_visual_symbol = "[❮](bold info)"

            [status]
            disabled = false
            style = "bold error"
            symbol = "✖"
            # Leerer success_symbol: status erscheint nur bei Exit != 0.
            success_symbol = ""
            format = "[$symbol $status]($style) "

            [username]
            show_always = false
            style_user = "muted"
            style_root = "bold error"
            format = "[$user]($style) "

            [hostname]
            ssh_only = true
            style = "muted"
            format = "[@$hostname]($style) "

            [directory]
            style = "bold interactive"
            read_only = " ro"
            read_only_style = "muted"
            truncation_length = 4
            truncation_symbol = "…/"
            format = "[$path]($style)[$read_only]($read_only_style) "

            [git_branch]
            symbol = ""
            style = "bold accent"
            format = "[$branch]($style) "

            [git_status]
            style = "error"
            format = "([$all_status$ahead_behind]($style)) "

            [git_state]
            style = "warm"
            format = "[$state]($style) "

            [cmd_duration]
            min_time = 500
            style = "bold warm"
            format = "[$duration]($style) "

            [jobs]
            symbol = "+"
            style = "muted"
            format = "[$symbol$number]($style) "

            [shell]
            style = "faint"
            format = "[$indicator]($style) "
            bash_indicator = "sh"
            zsh_indicator = "zsh"
            fish_indicator = "fish"
            powershell_indicator = "ps"

            [time]
            disabled = false
            time_format = "%H:%M"
            style = "muted"
            format = "[$time]($style)"

            # Sprachen und Tools: Versionen in Petrol, Blau oder Gold.
            [python]
            style = "accent"
            format = "[py $version]($style) "

            [nodejs]
            style = "interactive"
            format = "[node $version]($style) "

            [deno]
            style = "interactive"
            format = "[deno $version]($style) "

            [bun]
            style = "warm"
            format = "[bun $version]($style) "

            [rust]
            style = "warm"
            format = "[rs $version]($style) "

            [golang]
            style = "accent"
            format = "[go $version]($style) "

            [java]
            style = "interactive"
            format = "[java $version]($style) "

            [kotlin]
            style = "warm"
            format = "[kt $version]($style) "

            [ruby]
            style = "warm"
            format = "[rb $version]($style) "

            [php]
            style = "interactive"
            format = "[php $version]($style) "

            [elixir]
            style = "accent"
            format = "[ex $version]($style) "

            [haskell]
            style = "warm"
            format = "[hs $version]($style) "

            [lua]
            style = "interactive"
            format = "[lua $version]($style) "

            [perl]
            style = "warm"
            format = "[pl $version]($style) "

            [swift]
            style = "warm"
            format = "[swift $version]($style) "

            [zig]
            style = "accent"
            format = "[zig $version]($style) "

            [dotnet]
            style = "interactive"
            format = "[.net $version]($style) "

            [terraform]
            style = "accent"
            format = "[tf $version]($style) "

            [kubernetes]
            style = "interactive"
            format = "[k8s $context]($style) "

            [docker_context]
            style = "interactive"
            format = "[docker $context]($style) "

            [aws]
            style = "warm"
            format = "[aws $profile]($style) "

            [package]
            style = "faint"
            format = "[$version]($style) "
            """
        ).rstrip()
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# dircolors.gnu / LS_COLORS
# ---------------------------------------------------------------------------

ANSI_CODES = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}


def sgr(spec: str) -> str:
    """Turn 'bold red on_green' into an SGR sequence such as 01;31;42."""
    parts: list[str] = []
    for token in spec.split():
        if token == "bold":
            parts.append("01")
        elif token.startswith("on_"):
            parts.append(str(ANSI_CODES[token[3:]] + 10))
        else:
            parts.append(str(ANSI_CODES[token]))
    return ";".join(parts)


# LEFTCODE/RIGHTCODE/ENDCODE/CLRTOEOL are *control sequences*, not SGR numbers:
# GNU ls writes them verbatim around the SGR value of an entry. The backslash
# escapes stay literal in dircolors.gnu (dircolors passes them through) and are
# decoded by ls when it parses LS_COLORS. LEFTCODE + SGR + RIGHTCODE yields the
# usual "\e[01;34m", ENDCODE closes it, CLRTOEOL clears to end of line.
LS_LEFTCODE = r"\e["
LS_RIGHTCODE = "m"
LS_ENDCODE = r"\e[0m"
LS_CLRTOEOL = r"\e[K"

FIXED_LS = [
    ("NORMAL", "00"),
    ("FILE", "00"),
    ("RESET", "0"),
    ("DIR", sgr("bold blue")),
    ("LINK", sgr("bold cyan")),
    ("SYMLINK", sgr("bold cyan")),
    ("FIFO", sgr("bold yellow")),
    ("SOCK", sgr("bold magenta")),
    ("DOOR", sgr("bold magenta")),
    ("BLK", sgr("bold yellow on_black")),
    ("CHR", sgr("bold yellow on_black")),
    ("ORPHAN", sgr("bold red")),
    ("MISSING", sgr("bold red")),
    ("EXEC", sgr("bold green")),
    ("LEFTCODE", LS_LEFTCODE),
    ("RIGHTCODE", LS_RIGHTCODE),
    ("ENDCODE", LS_ENDCODE),
    ("SUID", sgr("bold white on_red")),
    ("SGID", sgr("bold white on_cyan")),
    ("STICKY_OTHER_WRITABLE", sgr("black on_green")),
    ("OTHER_WRITABLE", sgr("blue on_green")),
    ("STICKY", sgr("white on_blue")),
    ("CAPABILITY", sgr("black on_red")),
    ("MULTIHARDLINK", "00"),
    ("CLRTOEOL", LS_CLRTOEOL),
]

EXTENSION_GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "Archive",
        "bold red",
        [
            ".7z", ".ar", ".bz", ".bz2", ".cab", ".cpio", ".gz", ".lz", ".lz4",
            ".lzh", ".lzma", ".rar", ".tar", ".tar.bz2", ".tar.gz", ".tar.xz",
            ".tar.zst", ".taz", ".tbz", ".tbz2", ".tgz", ".tlz", ".txz", ".xz",
            ".z", ".zip", ".zst",
        ],
    ),
    (
        "Audio",
        "cyan",
        [
            ".aac", ".aiff", ".au", ".flac", ".m4a", ".mid", ".midi", ".mka",
            ".mp3", ".mpc", ".ogg", ".opus", ".ra", ".wav", ".wma",
        ],
    ),
    (
        "Bilder",
        "magenta",
        [
            ".ani", ".avif", ".bmp", ".cin", ".dds", ".exr", ".gif", ".heic",
            ".heif", ".ico", ".jpeg", ".jpg", ".jxl", ".mng", ".pbm", ".pcx",
            ".pgm", ".png", ".pnm", ".ppm", ".psd", ".ras", ".rgb", ".svg",
            ".tga", ".tif", ".tiff", ".webp", ".xbm", ".xcf", ".xpm", ".xwd",
        ],
    ),
    (
        "Video",
        "bold magenta",
        [
            ".3g2", ".3gp", ".avi", ".flv", ".m2v", ".m4v", ".mkv", ".mov",
            ".mp4", ".mpeg", ".mpg", ".ogm", ".ogv", ".qt", ".rm", ".rmvb",
            ".vob", ".webm", ".wmv",
        ],
    ),
    (
        "Dokumente",
        "yellow",
        [
            ".doc", ".docx", ".epub", ".mobi", ".odp", ".ods", ".odt", ".pdf",
            ".ppt", ".pptx", ".rtf", ".tex", ".xls", ".xlsx",
        ],
    ),
    (
        "Quellcode",
        "green",
        [
            ".awk", ".bash", ".c", ".cc", ".clj", ".cljc", ".cljs", ".cmd",
            ".cpp", ".cs", ".cxx", ".d", ".dart", ".el", ".erl", ".ex", ".exs",
            ".fish", ".go", ".gradle", ".groovy", ".h", ".hh", ".hpp", ".hrl",
            ".hs", ".hxx", ".java", ".jl", ".kt", ".kts", ".lhs", ".lisp",
            ".lua", ".m", ".mm", ".nix", ".php", ".pl", ".pm", ".ps1", ".py",
            ".r", ".rb", ".rs", ".scala", ".scm", ".sed", ".sh", ".sql",
            ".swift", ".ts", ".vim", ".zig", ".zsh",
        ],
    ),
    (
        "Web und Konfiguration",
        "blue",
        [
            ".cjs", ".conf", ".cfg", ".css", ".dockerignore", ".editorconfig",
            ".env", ".gitattributes", ".gitconfig", ".gitignore", ".htm",
            ".html", ".ini", ".js", ".json", ".json5", ".jsonc", ".jsx",
            ".less", ".lock", ".mjs", ".npmrc", ".properties", ".sass",
            ".scss", ".svelte", ".toml", ".tsx", ".vue", ".xhtml", ".xml",
            ".xsl", ".xslt", ".yaml", ".yarnrc", ".yml",
        ],
    ),
    ("Diff: geaendert", "bold yellow", [".diff"]),
    ("Diff: Patch", "bold cyan", [".patch"]),
    ("Diff: abgelehnt", "bold red", [".rej"]),
    (
        "Build-Artefakte",
        "bright_black",
        [
            ".a", ".apk", ".appimage", ".beam", ".bin", ".class", ".db", ".dll",
            ".dmg", ".dylib", ".ear", ".exe", ".hi", ".img", ".iso", ".jar",
            ".lib", ".map", ".msi", ".o", ".obj", ".out", ".pkg", ".pyc",
            ".pyo", ".snap", ".so", ".sqlite", ".sqlite3", ".war", ".wasm",
        ],
    ),
    (
        "Sicherungen, Temp, Logs",
        "bright_black",
        [
            ".bak", ".cache", ".log", ".old", ".orig", ".pid", ".swo", ".swp",
            ".swn", ".temp", ".tmp",
        ],
    ),
]


def build_dircolors() -> str:
    lines = [
        f"# {HEADER}",
        "# GNU dircolors-Format: eval \"$(dircolors /pfad/zu/dircolors.gnu)\"",
        "# macOS /bin/ls nutzt LSCOLORS, nicht diese Datei; siehe lscolors.bsd.",
        "#",
        "# Werte: alle Eintraege sind SGR-Codes (z.B. 01;34), AUSSER",
        "#   LEFTCODE  \\e[   RIGHTCODE  m   ENDCODE  \\e[0m   CLRTOEOL  \\e[K",
        "# Diese vier sind Steuersequenzen, die ls woertlich schreibt; SGR-Zahlen",
        "# an dieser Stelle erzeugen Ausgaben wie '0001;3401;34name00'.",
        "#",
        "# ANSI-Zuordnung (Dark):",
    ]
    for name, value in ANSI["dark"].items():
        lines.append(f"#   {name:<20} {value}  SGR {ANSI_CODES[name]}")
    lines.append("")

    for key, value in FIXED_LS:
        lines.append(f"{key} {value}")

    seen: set[str] = set()
    for title, spec, extensions in EXTENSION_GROUPS:
        lines.append("")
        lines.append(f"# {title}")
        for extension in extensions:
            if extension in seen:
                raise SystemExit(f"build.py: doppelte LS_COLORS-Endung {extension}")
            seen.add(extension)
            lines.append(f"{extension} {sgr(spec)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# lscolors.bsd
# ---------------------------------------------------------------------------


def build_lscolors_bsd() -> str:
    # macOS ls(1): 11 pairs = directory, symlink, socket, pipe, executable,
    # block special, char special, setuid, setgid, sticky+writable, writable.
    pairs = "ExGxFxdxCxDxDxBxBxExEx"
    assert len(pairs) == 22
    return textwrap.dedent(
        f"""\
        # {HEADER}
        # macOS/BSD ls: LSCOLORS besteht aus 11 Paaren (Vordergrund/Hintergrund).
        # Reihenfolge: Verzeichnis, Symlink, Socket, Pipe, Executable,
        # Block-, Zeichengeraet, setuid, setgid, sticky+writable, writable.
        # Kuerzel: a=schwarz b=rot c=gruen d=braun e=blau f=magenta g=cyan
        #          h=hellgrau; Grossbuchstabe=fett; x=Terminal-Default.
        # Achtung: 8 Paare (16 Zeichen) waeren ungueltig; macOS ls(1)
        # dokumentiert 11 Paare. GNU ls nutzt LS_COLORS -> dircolors.gnu.
        export CLICOLOR=1
        export LSCOLORS="{pairs}"
        """
    )


# ---------------------------------------------------------------------------
# bat/42vibes.tmTheme
# ---------------------------------------------------------------------------

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>'
PLIST_DOCTYPE = (
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
)


def xml_add(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, tag)
    if text is not None:
        element.text = text
    return element


def xml_kv(parent: ET.Element, key: str, value: str) -> None:
    xml_add(parent, "key", key)
    xml_add(parent, "string", value)


def build_tmtheme(mode: str, name: str) -> str:
    sem = SEM[mode]
    ramp = DARK_RAMP if mode == "dark" else LIGHT_RAMP

    def c(hue: str, step: str) -> str:
        return ramp[hue][step]

    root = ET.Element("plist", {"version": "1.0"})
    top = ET.SubElement(root, "dict")
    xml_kv(top, "name", name)
    xml_kv(top, "semanticClass", f"theme.{name}")

    xml_add(top, "key", "settings")
    settings = ET.SubElement(top, "array")

    global_entry = ET.SubElement(settings, "dict")
    xml_add(global_entry, "key", "settings")
    global_settings = ET.SubElement(global_entry, "dict")
    for key, value in [
        ("background", sem["bg"]),
        ("foreground", sem["text"]),
        ("caret", c("green", "300")),
        ("lineHighlight", sem["surface"]),
        ("selection", sem["surface_high"]),
        ("selectionForeground", sem["text"]),
        ("inactiveSelection", sem["surface"]),
        # On light backgrounds the semantic warm tone is too weak as a text
        # background; the 500 step keeps >= 4.5:1 against the light bg.
        ("findHighlight", sem["warm"] if mode == "dark" else c("yellow", "500")),
        ("findHighlightForeground", sem["bg"]),
        ("invisibles", sem["text_faint"]),
        ("gutter", sem["bg"]),
        ("gutterForeground", c("gray", "400")),
    ]:
        xml_kv(global_settings, key, value)

    scopes: list[dict[str, str]] = [
        {"name": "Comment", "scope": "comment, punctuation.definition.comment", "foreground": c("gray", "400"), "fontStyle": "italic"},
        {"name": "Documentation comment", "scope": "comment.block.documentation", "foreground": c("gray", "300"), "fontStyle": "italic"},
        {"name": "Keyword", "scope": "keyword, storage", "foreground": c("purple", "300")},
        {"name": "Keyword control", "scope": "keyword.control", "foreground": c("purple", "300")},
        {"name": "Storage type", "scope": "storage.type", "foreground": c("purple", "300")},
        {"name": "String", "scope": "string", "foreground": c("green", "300")},
        {"name": "String regexp", "scope": "string.regexp", "foreground": c("cyan", "300")},
        {"name": "String escape", "scope": "string.escape, constant.character.escape", "foreground": c("yellow", "300")},
        {"name": "Number", "scope": "constant.numeric", "foreground": c("orange", "300")},
        {"name": "Constant", "scope": "constant, support.constant", "foreground": c("yellow", "300")},
        {"name": "Constant language", "scope": "constant.language", "foreground": c("orange", "300")},
        {"name": "Variable", "scope": "variable", "foreground": c("gray", "200")},
        {"name": "Variable parameter", "scope": "variable.parameter", "foreground": c("gray", "300")},
        {"name": "Variable language", "scope": "variable.language", "foreground": c("purple", "300")},
        {"name": "Function", "scope": "function, entity.name.function, support.function", "foreground": c("blue", "300")},
        {"name": "Type", "scope": "type, entity.name.type, entity.name.class, support.type", "foreground": c("cyan", "300")},
        {"name": "Operator", "scope": "operator", "foreground": c("gray", "300")},
        {"name": "Punctuation", "scope": "punctuation, punctuation.separator", "foreground": c("gray", "400")},
        {"name": "Tag", "scope": "entity.name.tag", "foreground": c("blue", "300")},
        {"name": "Attribute", "scope": "entity.other.attribute-name", "foreground": c("yellow", "300")},
        {"name": "Preprocessor", "scope": "meta.preprocessor", "foreground": c("purple", "300")},
        {"name": "Markup heading", "scope": "markup.heading", "foreground": c("green", "300"), "fontStyle": "bold"},
        {"name": "Markup bold", "scope": "markup.bold", "foreground": c("gray", "100"), "fontStyle": "bold"},
        {"name": "Markup strong", "scope": "markup.strong", "foreground": c("gray", "100"), "fontStyle": "bold"},
        {"name": "Markup italic", "scope": "markup.italic", "foreground": c("gray", "200"), "fontStyle": "italic"},
        {"name": "Markup underline", "scope": "markup.underline", "foreground": c("blue", "300"), "fontStyle": "underline"},
        {"name": "Markup link", "scope": "markup.link", "foreground": c("blue", "300"), "fontStyle": "underline"},
        {"name": "Markup quote", "scope": "markup.quote", "foreground": c("gray", "400"), "fontStyle": "italic"},
        {"name": "Markup raw", "scope": "markup.raw", "foreground": c("green", "300")},
        {"name": "Markup inserted", "scope": "markup.inserted", "foreground": c("green", "300")},
        {"name": "Markup deleted", "scope": "markup.deleted", "foreground": c("red", "300")},
        {"name": "Markup changed", "scope": "markup.changed", "foreground": c("yellow", "300")},
        {"name": "Invalid", "scope": "invalid", "foreground": c("red", "200"), "background": c("red", "900")},
        {"name": "Invalid deprecated", "scope": "invalid.deprecated", "foreground": c("orange", "300"), "fontStyle": "underline"},
    ]

    for spec in scopes:
        entry = ET.SubElement(settings, "dict")
        xml_kv(entry, "name", spec["name"])
        xml_kv(entry, "scope", spec["scope"])
        xml_add(entry, "key", "settings")
        inner = ET.SubElement(entry, "dict")
        xml_kv(inner, "foreground", spec["foreground"])
        if "background" in spec:
            xml_kv(inner, "background", spec["background"])
        if "fontStyle" in spec:
            xml_kv(inner, "fontStyle", spec["fontStyle"])

    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return f"{XML_DECL}\n{PLIST_DOCTYPE}\n{body}"


# ---------------------------------------------------------------------------
# delta.gitconfig
# ---------------------------------------------------------------------------


def build_delta() -> str:
    return textwrap.dedent(
        f"""\
        # {HEADER}
        # Einbinden mit:  [include] path = /pfad/zu/delta.gitconfig
        #
        # Bewusst ANSI-Farbnamen statt Hex: delta akzeptiert seit neueren
        # Versionen "#rrggbb", ANSI-Namen funktionieren aber auch in aelteren
        # Versionen und ohne Truecolor. Hex-Werte stehen im README.
        # Rollen: blau = Datei/Pfad, petrol/gruen = plus, rot = minus,
        #         gold/gelb = Hunk und Commit, cyan = Zeilennummern.
        # Zwei Features: "42vibes" (dunkel, Default) und "42vibes-light".

        [core]
        	pager = delta

        [interactive]
        	diffFilter = delta --color-only

        [delta]
        	navigate = true
        	line-numbers = true
        	side-by-side = true
        	syntax-theme = 42vibes
        	features = 42vibes
        	hyperlinks = true

        [delta "42vibes"]
        	# Datei-Kopf
        	file-style = "bold blue"
        	file-decoration-style = "blue ul"
        	# Hunk-Kopf
        	hunk-header-style = "bold yellow"
        	hunk-header-decoration-style = "yellow box"
        	# Zeilennummern
        	line-numbers-left-style = "cyan"
        	line-numbers-right-style = "cyan"
        	line-numbers-minus-style = "red"
        	line-numbers-plus-style = "green"
        	line-numbers-zero-style = "brightblack"
        	# Entfernte Zeilen (minus)
        	minus-style = "red"
        	minus-emph-style = "bold red"
        	minus-empty-line-marker-style = "red"
        	# Hinzugefuegte Zeilen (plus)
        	plus-style = "green"
        	plus-emph-style = "bold green"
        	plus-empty-line-marker-style = "green"
        	# Commit und Metadaten
        	commit-style = "bold yellow"
        	commit-decoration-style = "yellow box"
        	whitespace-error-style = "magenta reverse"

        [delta "42vibes-light"]
        	# Gleiche ANSI-Rollen wie dunkel: die konkreten Light-Farben
        	# kommen aus den ANSI-Slots 0-15 des hellen Terminal-Profils.
        	# Kein Hex, damit aeltere delta-Versionen und Terminals ohne
        	# Truecolor mitmachen (Grenze siehe README).
        	light = true
        	# Datei-Kopf
        	file-style = "bold blue"
        	file-decoration-style = "blue ul"
        	# Hunk-Kopf
        	hunk-header-style = "bold yellow"
        	hunk-header-decoration-style = "yellow box"
        	# Zeilennummern
        	line-numbers-left-style = "cyan"
        	line-numbers-right-style = "cyan"
        	line-numbers-minus-style = "red"
        	line-numbers-plus-style = "green"
        	line-numbers-zero-style = "brightblack"
        	# Entfernte Zeilen (minus)
        	minus-style = "red"
        	minus-emph-style = "bold red"
        	minus-empty-line-marker-style = "red"
        	# Hinzugefuegte Zeilen (plus)
        	plus-style = "green"
        	plus-emph-style = "bold green"
        	plus-empty-line-marker-style = "green"
        	# Commit und Metadaten
        	commit-style = "bold yellow"
        	commit-decoration-style = "yellow box"
        	whitespace-error-style = "magenta reverse"
        """
    )


# ---------------------------------------------------------------------------
# palette.sh
# ---------------------------------------------------------------------------

SEMANTIC = [
    "bg", "bg_deep", "surface", "surface_high", "surface_max", "text",
    "text_muted", "text_faint", "accent", "interactive", "warm", "border",
    "success", "warning", "error", "info",
]
ANSI_NAMES = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]


def build_palette_sh() -> str:
    lines = [
        "#!/bin/sh",
        f"# {HEADER}",
        "# POSIX sh / bash 3.2: keine Arrays, keine Assoziativ-Arrays,",
        "# keine bash-4-Features. Einbinden mit:  . /pfad/zu/palette.sh",
        "",
    ]

    for mode, prefix in (("dark", "VIBES"), ("light", "VIBES_LIGHT")):
        lines.append(f"# {'Dark (Default)' if mode == 'dark' else 'Light'}")
        names: list[str] = []
        for key in SEMANTIC:
            name = f"{prefix}_{key.upper()}"
            lines.append(f"{name}='{SEM[mode][key]}'")
            names.append(name)
        for key in ANSI_NAMES:
            name = f"{prefix}_ANSI_{key.upper()}"
            lines.append(f"{name}='{ANSI[mode][key]}'")
            names.append(name)
        lines.append("export " + " ".join(names))
        lines.append("")

    short = {
        "C_BG": "VIBES_BG",
        "C_BG_DEEP": "VIBES_BG_DEEP",
        "C_SURFACE": "VIBES_SURFACE",
        "C_SURFACE_HIGH": "VIBES_SURFACE_HIGH",
        "C_SURFACE_MAX": "VIBES_SURFACE_MAX",
        "C_TEXT": "VIBES_TEXT",
        "C_MUTED": "VIBES_TEXT_MUTED",
        "C_FAINT": "VIBES_TEXT_FAINT",
        "C_ACCENT": "VIBES_ACCENT",
        "C_BLUE": "VIBES_INTERACTIVE",
        "C_GOLD": "VIBES_WARM",
        "C_BORDER": "VIBES_BORDER",
        "C_SUCCESS": "VIBES_SUCCESS",
        "C_WARNING": "VIBES_WARNING",
        "C_ERROR": "VIBES_ERROR",
        "C_INFO": "VIBES_INFO",
        "C_BLACK": "VIBES_ANSI_BLACK",
        "C_RED": "VIBES_ANSI_RED",
        "C_GREEN": "VIBES_ANSI_GREEN",
        "C_YELLOW": "VIBES_ANSI_YELLOW",
        "C_MAGENTA": "VIBES_ANSI_MAGENTA",
        "C_CYAN": "VIBES_ANSI_CYAN",
        "C_WHITE": "VIBES_ANSI_WHITE",
        "C_BRIGHT_BLACK": "VIBES_ANSI_BRIGHT_BLACK",
        "C_BRIGHT_RED": "VIBES_ANSI_BRIGHT_RED",
        "C_BRIGHT_GREEN": "VIBES_ANSI_BRIGHT_GREEN",
        "C_BRIGHT_YELLOW": "VIBES_ANSI_BRIGHT_YELLOW",
        "C_BRIGHT_BLUE": "VIBES_ANSI_BRIGHT_BLUE",
        "C_BRIGHT_MAGENTA": "VIBES_ANSI_BRIGHT_MAGENTA",
        "C_BRIGHT_CYAN": "VIBES_ANSI_BRIGHT_CYAN",
        "C_BRIGHT_WHITE": "VIBES_ANSI_BRIGHT_WHITE",
    }
    lines.append("# Kurzformen (Dark) fuer Skripte")
    for name, target in short.items():
        lines.append(f'{name}="${target}"')
    lines.append("export " + " ".join(short))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------


def md_semantic_table(lang: str) -> str:
    rows = [
        "| Role | Variable | Dark | Light |"
        if lang == "en"
        else "| Rolle | Variable | Dark | Light |",
        "| --- | --- | --- | --- |",
    ]
    for key in SEMANTIC:
        rows.append(
            f"| {key} | `VIBES_{key.upper()}` | `{SEM['dark'][key]}` | `{SEM['light'][key]}` |"
        )
    return "\n".join(rows)


def md_ansi_table(lang: str) -> str:
    rows = [
        "| Name | Dark | Light | SGR |",
        "| --- | --- | --- | --- |",
    ]
    for key in ANSI_NAMES:
        rows.append(
            f"| {key} | `{ANSI['dark'][key]}` | `{ANSI['light'][key]}` | {ANSI_CODES[key]} |"
        )
    return "\n".join(rows)


def md_mapping_table(lang: str) -> str:
    roles = {
        "en": [
            "Directory (bold)", "Git branch (bold)", "Error (bold/red)",
            "User/host (muted)", "Language/tool", "Comment", "Keyword", "String",
            "Number", "Constant", "Function", "Type", "Variable", "Heading",
            "Link", "Invalid", "Diff plus/minus",
        ],
        "de": [
            "Verzeichnis (fett)", "Git-Branch (fett)", "Fehler (fett/rot)",
            "User/Host (gedämpft)", "Sprache/Tool", "Kommentar", "Keyword", "String",
            "Zahl", "Konstante", "Funktion", "Typ", "Variable", "Überschrift",
            "Link", "Invalid", "Diff plus/minus",
        ],
    }[lang]
    header = (
        "| Role | Palette | Starship | bat scope |"
        if lang == "en"
        else "| Rolle | Palette | Starship | bat-Scope |"
    )
    rows = [
        header,
        "| --- | --- | --- | --- |",
        f"| {roles[0]} | `interactive` {SEM['dark']['interactive']} | `directory` → `bold interactive` | – |",
        f"| {roles[1]} | `accent` {SEM['dark']['accent']} | `git_branch` → `bold accent` | – |",
        f"| {roles[2]} | `error` {SEM['dark']['error']} | `character`/`status` → `bold error` | `invalid` |",
        f"| {roles[3]} | `muted` {SEM['dark']['text_muted']} | `username`/`hostname`/`time` → `muted` | – |",
        f"| {roles[4]} | petrol/blue/gold | `accent`/`interactive`/`warm` | – |",
        f"| {roles[5]} | `gray.400` {dark('gray', '400')} | – | `comment` (italic) |",
        f"| {roles[6]} | `purple.300` {dark('purple', '300')} | – | `keyword`, `storage` |",
        f"| {roles[7]} | `green.300` {dark('green', '300')} | – | `string` |",
        f"| {roles[8]} | `orange.300` {dark('orange', '300')} | – | `constant.numeric` |",
        f"| {roles[9]} | `yellow.300` {dark('yellow', '300')} | – | `constant` |",
        f"| {roles[10]} | `blue.300` {dark('blue', '300')} | – | `function` |",
        f"| {roles[11]} | `cyan.300` {dark('cyan', '300')} | – | `type` |",
        f"| {roles[12]} | `gray.200` {dark('gray', '200')} | – | `variable` |",
        f"| {roles[13]} | `green.300` {dark('green', '300')} | – | `markup.heading` (bold) |",
        f"| {roles[14]} | `blue.300` {dark('blue', '300')} | – | `markup.link` (underline) |",
        f"| {roles[15]} | `red.200`/`red.900` | – | `invalid` |",
        f"| {roles[16]} | ansi green/red | – | `markup.inserted`/`markup.deleted` |",
    ]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# preview/palette-*.svg
# ---------------------------------------------------------------------------

PREVIEW_WIDTH = 760
PREVIEW_PAD = 28
PREVIEW_ROW_H = 40
PREVIEW_SWATCH_W = 48
PREVIEW_SWATCH_H = 24
PREVIEW_COL_GAP = 24


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_palette_svg(mode: str) -> str:
    """Render semantic tokens and ANSI 0-15 as a pure SVG swatch sheet."""
    sem = SEM[mode]
    ansi = ANSI[mode]
    page_bg = sem["bg"]
    text = sem["text"]
    muted = sem["text_muted"]
    border = sem["border"]
    accent = sem["accent"]

    col_w = (PREVIEW_WIDTH - 2 * PREVIEW_PAD - PREVIEW_COL_GAP) // 2
    title_y = PREVIEW_PAD + 20
    subtitle_y = PREVIEW_PAD + 42
    semantic_label_y = PREVIEW_PAD + 76
    semantic_top = PREVIEW_PAD + 88
    ansi_label_y = semantic_top + 8 * PREVIEW_ROW_H + 26
    ansi_top = ansi_label_y + 12
    height = ansi_top + 8 * PREVIEW_ROW_H + PREVIEW_PAD
    label = "Dark" if mode == "dark" else "Light"

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PREVIEW_WIDTH}" '
        f'height="{height}" viewBox="0 0 {PREVIEW_WIDTH} {height}" '
        f'role="img" font-family="ui-monospace, monospace">',
        f"  <title>42vibes palette preview ({label})</title>",
        f'  <rect width="{PREVIEW_WIDTH}" height="{height}" fill="{page_bg}"/>',
        f'  <text x="{PREVIEW_PAD}" y="{title_y}" fill="{accent}" font-size="22" '
        f'font-weight="bold" font-family="ui-monospace, monospace">'
        f"42vibes · {label}</text>",
        f'  <text x="{PREVIEW_PAD}" y="{subtitle_y}" fill="{muted}" font-size="13" '
        f'font-family="ui-monospace, monospace">Semantische Tokens und ANSI 0–15, '
        f"generiert aus vendor/palette.json</text>",
        f'  <line x1="{PREVIEW_PAD}" y1="{subtitle_y + 12}" '
        f'x2="{PREVIEW_WIDTH - PREVIEW_PAD}" y2="{subtitle_y + 12}" '
        f'stroke="{border}" stroke-width="1"/>',
        f'  <text x="{PREVIEW_PAD}" y="{semantic_label_y}" fill="{muted}" '
        f'font-size="12" letter-spacing="1.5" '
        f'font-family="ui-monospace, monospace">SEMANTIC</text>',
    ]

    def add_rows(items: list[tuple[str, str]], top: int) -> None:
        for index, (name, value) in enumerate(items):
            column, row = divmod(index, 8)
            x = PREVIEW_PAD + column * (col_w + PREVIEW_COL_GAP)
            y = top + row * PREVIEW_ROW_H
            swatch_y = y + (PREVIEW_ROW_H - PREVIEW_SWATCH_H) // 2
            baseline = y + PREVIEW_ROW_H // 2 + 4
            text_x = x + PREVIEW_SWATCH_W + 12
            hex_x = x + col_w - 4
            out.extend(
                [
                    f'  <rect x="{x}" y="{swatch_y}" width="{PREVIEW_SWATCH_W}" '
                    f'height="{PREVIEW_SWATCH_H}" rx="4" fill="{value}" '
                    f'stroke="{border}" stroke-width="1"/>',
                    f'  <text x="{text_x}" y="{baseline}" fill="{text}" '
                    f'font-size="13" font-family="ui-monospace, monospace">'
                    f"{xml_escape(name)}</text>",
                    f'  <text x="{hex_x}" y="{baseline}" fill="{muted}" '
                    f'font-size="12" text-anchor="end" '
                    f'font-family="ui-monospace, monospace">{value}</text>',
                ]
            )

    add_rows([(key, sem[key]) for key in SEMANTIC], semantic_top)
    out.append(
        f'  <text x="{PREVIEW_PAD}" y="{ansi_label_y}" fill="{muted}" '
        f'font-size="12" letter-spacing="1.5" '
        f'font-family="ui-monospace, monospace">ANSI 0–15</text>'
    )
    add_rows(
        [(f"{index} {name}", ansi[name]) for index, name in enumerate(ANSI_NAMES)],
        ansi_top,
    )
    out.append("</svg>")
    return "\n".join(out)


README_TEMPLATE_EN = """\
# 42vibes – Shell and tool profiles

**English** · [Deutsch](README.de.md)

A standalone profile set for Starship, `ls`/dircolors, bat and delta, derived
from the 42vibes palette (`vendor/palette.json`). Everything is meant as a
copy template: this repo installs nothing globally and does not change any
user config.

## Order: terminal profile first

The colors only work together if the terminal profile sets the base.
Recommended order:

1. **Terminal profile** (background, foreground, cursor, selection, ANSI 16)
2. **Starship** (`starship.toml`)
3. **bat** (`bat/42vibes.tmTheme`, `bat/42vibes-light.tmTheme`)
4. **delta** (`delta.gitconfig`)
5. **ls colors** (`dircolors.gnu` for GNU ls, `lscolors.bsd` for macOS `/bin/ls`)
6. **`palette.sh`** in your own scripts

Why the terminal first? Starship and bat speak hex/truecolor, `ls` and delta
speak ANSI names. If the ANSI slots in the terminal do not match the palette,
the same roles look different in the tools.

## Palette

The preview below is generated: `build.py` creates both SVGs from
`vendor/palette.json`. These are not screenshots; please do not edit them by
hand.

**Dark**

![Generated palette preview Dark: semantic tokens and ANSI 0–15](preview/palette-dark.svg)

**Light**

![Generated palette preview Light: semantic tokens and ANSI 0–15](preview/palette-light.svg)

Semantic tokens (dark/light):

{{SEMANTIC_TABLE}}

The hue ramps are built in HSL: only lightness moves, hue and saturation stay
the same. The steps are identical to the other 42vibes targets (dark
`+0.28 … -0.38`, light `-0.30 … +0.28`, saturation ×0.55 at 100/900).

### ANSI order

{{ANSI_TABLE}}

These 16 values belong in the terminal profile. `dircolors.gnu` and
`lscolors.bsd` use exactly these slots; they cannot output hex.

## Starship

`starship.toml` contains two palettes: `[palettes.42vibes]` (dark, default)
and `[palettes.42vibes_light]`. The active palette is set at the top as
`palette = "42vibes"`; change it to `42vibes_light` for a light background.

Include it without overwriting the global config:

```sh
export STARSHIP_CONFIG="$PWD/starship.toml"
# or: cp starship.toml ~/.config/starship.toml
```

Prompt style:

- Status **bold/red**, only on a non-zero exit code (`status`, empty
  `success_symbol`); the character switches to the red error symbol.
- User/host **muted** and only shown when relevant (`username.show_always =
  false`, `hostname.ssh_only = true`).
- Directory **bold** in blue (`directory` → `bold interactive`).
- Git branch **bold** in petrol (`git_branch` → `bold accent`).
- Truncation: `truncation_symbol = "…/"` is plain text, not a format string,
  and inherits the directory style; the current directory name stays bold.
- Language and tool versions in petrol, blue or gold (`python`, `nodejs`,
  `rust`, `golang`, …) on the second prompt line; that line also carries
  contextual modules such as `git_state`, `cmd_duration`, `jobs`, `package`,
  `kubernetes`, `docker_context`, `aws`, `shell` and `time`.

**No Nerd Font requirement:** the profile only uses regular Unicode characters
(`❯`, `╭`, `╰`, `…`) and text labels such as `py`, `node`, `rs`. If you want
Nerd Font symbols, you can add them to the `format` lines of the modules.

## File colors: GNU ls vs. macOS ls

These are two different mechanisms – do not mix them up:

| | GNU ls (Linux, coreutils) | macOS `/bin/ls` (BSD) |
| --- | --- | --- |
| Variable | `LS_COLORS` | `LSCOLORS` (+ `CLICOLOR=1`) |
| Generator | `dircolors` | none |
| File here | `dircolors.gnu` | `lscolors.bsd` |
| Scope | 16 ANSI colors + any number of extensions | 11 attribute pairs, 8 colors |
| Hex/truecolor | no (SGR) | no |

### GNU ls: `dircolors.gnu`

```sh
eval "$(dircolors /path/to/dircolors.gnu)"
```

The file is a complete GNU `LS_COLORS` set: standard types, SUID/SGID/sticky,
archives, audio, images, video, documents, source code, web/configuration,
build artifacts and backups. Diff files are deliberately separate roles:
`.diff` bold yellow, `.patch` bold cyan, `.rej` bold red, `.orig` muted. That
keeps them distinguishable from green/red for added and removed lines.

`LEFTCODE`, `RIGHTCODE`, `ENDCODE` and `CLRTOEOL` do **not** hold SGR numbers:
they are control sequences (`\\e[`, `m`, `\\e[0m`, `\\e[K`) that `ls` writes
verbatim around the SGR value of an entry. Every other value is a plain SGR
sequence such as `01;34`. SGR numbers in those four slots would end up as
literal text, e.g. `0001;3401;34name00`.

Check: `dircolors -b dircolors.gnu` (exit 0).

### macOS `/bin/ls`: `lscolors.bsd`

```sh
. /path/to/lscolors.bsd
```

The script sets `CLICOLOR=1` and `LSCOLORS`. **Important:** macOS `ls(1)`
documents **11 pairs** – directory, symlink, socket, pipe, executable, block
device, character device, setuid, setgid, sticky+writable, writable. An
8-pair value (16 characters) is rejected by `/bin/ls`; `lscolors.bsd`
therefore correctly uses 11 pairs (22 characters).

`/bin/ls` ignores `LS_COLORS` completely. If you use GNU ls on macOS
(Homebrew `coreutils`, commands `gls` and `gdircolors`), use `dircolors.gnu`
instead:

```sh
eval "$(gdircolors /path/to/dircolors.gnu)"
alias ls='gls --color=auto'
```

## bat

```sh
mkdir -p "$(bat --config-dir)/themes"
cp bat/42vibes.tmTheme bat/42vibes-light.tmTheme "$(bat --config-dir)/themes/"
bat cache --build
export BAT_THEME=42vibes          # dark background
# export BAT_THEME=42vibes-light  # light background
bat --list-themes | grep 42vibes
```

`bat --theme` takes a theme *name* that bat knows from its cache, not a file
path. The copy and `bat cache --build` steps above are therefore required;
after that, `bat --theme=42vibes file` works (or use `BAT_THEME`).

Both themes are valid tmThemes (XML/plist) with the same scopes: comment,
keyword, string, number, constant, function, type, variable, operator, markup
(heading/strong/link/quote) and `invalid`. `42vibes` uses the dark ramps,
`42vibes-light` the same ramps and scopes based on the light values.
Comments and quotes are italic, headings and strong bold, links underlined.
`validate.py` checks the required scopes and sensible contrasts for both files
(text/syntax ≥ 4.5:1, auxiliary colors ≥ 3:1).

## delta

`delta.gitconfig` is a snippet, not a global change. Include it:

```gitconfig
[include]
    path = /path/to/delta.gitconfig
```

or per invocation `git -c include.path=/path/to/delta.gitconfig diff`.

The snippet sets `[core] pager = delta`, `[interactive] diffFilter` and two
features: `[delta "42vibes"]` (dark, default) and
`[delta "42vibes-light"]` (light). Color roles: blue for file/path,
yellow/gold for hunk and commit, red for removed lines and line numbers,
green for added lines, cyan for neutral line numbers.

Activate the light feature after including the snippet. Place the `[include]`
before any `[delta]` section so the snippet's `features = 42vibes` does not
win:

```sh
git config --global include.path /path/to/delta.gitconfig
git config --global delta.features 42vibes-light   # light
git config --global delta.features 42vibes          # back to dark
```

For a single invocation use `git -c delta.features=42vibes-light diff`.

**Light limits:** `42vibes-light` uses ANSI names, not hex. Its actual colors
therefore come from ANSI slots 0–15 of the terminal profile; use the light
terminal profile. The snippet's `[delta] syntax-theme = 42vibes` is a
top-level option, and delta gives `[delta]` precedence over features, so the
light feature cannot switch the syntax theme. For light syntax highlighting
use `git -c delta.syntax-theme=42vibes-light diff`; the bat theme must be
known via `bat cache --build`.

**Hex note:** delta accepts `#rrggbb` in style values in newer versions, but
not reliably in older versions and terminals without truecolor. The snippet
therefore uses ANSI names for both features. The matching hex values are in
the palette table; to test, use `delta --version` and `git diff`.

## palette.sh

POSIX sh compatible and suitable for macOS bash 3.2: no arrays, no associative
arrays, no bash 4 features.

```sh
. /path/to/palette.sh
printf '%s\\n' "$C_ACCENT" "$VIBES_BG" "$VIBES_ANSI_RED"
```

Exported are:

- `VIBES_*` for dark (default) and `VIBES_LIGHT_*` for light,
- `VIBES_ANSI_*` and `VIBES_LIGHT_ANSI_*` for the 16 ANSI slots,
- short `C_*` variables (dark): `C_BG`, `C_TEXT`, `C_MUTED`, `C_ACCENT`,
  `C_BLUE`, `C_GOLD`, `C_ERROR`, `C_RED`, `C_GREEN`, `C_YELLOW`, …

The file is **sourced**, not executed – otherwise the exports disappear with
the subshell. If you need escape sequences, build them from the hex values
yourself; `palette.sh` only provides color values.

## macOS differences

- **`/bin/ls` vs. GNU ls:** macOS `/bin/ls` reads `LSCOLORS` (`lscolors.bsd`),
  GNU ls reads `LS_COLORS` (`dircolors.gnu`). `dircolors` does not exist on
  macOS; Homebrew coreutils provides `gdircolors` and `gls`.
- **bash 3.2:** `palette.sh` avoids arrays and bash 4 syntax. `source` works,
  `.` is POSIX and also fine.
- **Terminal.app:** no truecolor. Hex colors from Starship/bat are mapped to
  256/16 colors; ANSI-based tools (`ls`, delta) stay exact. For exact hex
  values use iTerm2, Kitty, WezTerm or Ghostty with `COLORTERM=truecolor`.

## Bold and truecolor

- Starship: `bold` is a style token (`bold interactive`). Some terminals
  render “bold” as a bright color rather than as a font weight.
- bat: `fontStyle` `bold`/`italic`/`underline`; if the font cannot do that,
  the text stays colored but without the face.
- If a terminal does not render bold, remove `bold` from the styles – the
  roles remain recognizable through color and position.
- Truecolor: check `COLORTERM=truecolor` (`printf '%s\\n' "$COLORTERM"`).
  Without truecolor, hex values are approximated.

## Color mapping Starship/bat

{{MAPPING_TABLE}}

The table shows the dark values. `42vibes-light.tmTheme` uses the same scopes
with the light ramps; `validate.py` checks the contrasts for both themes.

## Build and check

```sh
python3 build.py          # regenerates all generated files
python3 build.py --check  # checks that the checked-in files are current
python3 validate.py       # TOML, XML, sh -n, dircolors, git config, LSCOLORS
make check                # both
```

`build.py` is the source of truth. To change colors, update
`vendor/palette.json` from `../42vibes-palette`, then run `make build validate`.
`README.md`, `README.de.md`, `starship.toml`, `dircolors.gnu`, `lscolors.bsd`,
`bat/42vibes.tmTheme`, `bat/42vibes-light.tmTheme`, `delta.gitconfig`,
`palette.sh`, `preview/palette-dark.svg` and `preview/palette-light.svg` are
generated and checked in.

## Structure

```text
.
├── build.py                 # generator (palette -> all artifacts)
├── validate.py              # structural and syntactic checks
├── Makefile                 # build / validate / check
├── vendor/palette.json      # copy of the shared palette
├── starship.toml            # generated
├── dircolors.gnu            # generated (GNU ls)
├── lscolors.bsd             # generated (macOS /bin/ls)
├── bat/42vibes.tmTheme     # generated (bat, dark)
├── bat/42vibes-light.tmTheme  # generated (bat, light)
├── delta.gitconfig          # generated (git/delta)
├── palette.sh               # generated (POSIX sh)
└── preview/
    ├── palette-dark.svg     # generated (palette preview)
    └── palette-light.svg    # generated (palette preview)
```

## Open issues

- **delta and hex:** the snippet uses ANSI names. Hex is possible in new delta
  versions but not safe in every environment; if needed, use the hex values
  from the palette table and test.
- **LSCOLORS pairs:** the requirement was 8 pairs, macOS `ls(1)` demands 11.
  The file follows the macOS documentation; 8 pairs would be invalid.
- **Light variants:** Starship and bat have light variants (`42vibes_light`,
  `42vibes-light.tmTheme`); delta has the `42vibes-light` feature, but it
  uses ANSI names and keeps the dark syntax theme unless overridden (see
  delta). `dircolors.gnu` and `lscolors.bsd` are tuned to the dark background.
  The light values are in the palette table for your own derivations.
- **Terminal.app:** no truecolor; hex colors are approximated.
- **Nerd Font:** deliberately no private-use glyphs; symbols are optional.
- **delta `syntax-theme`:** assumes the bat theme is installed and known via
  `bat cache --build`.

## License

MIT, Copyright 2026 42vibes. The full text is in [`LICENSE`](LICENSE).
"""


README_TEMPLATE_DE = """\
# 42vibes – Shell- und Tool-Profile

[English](README.md) · **Deutsch**

Ein eigenständiges Profil-Set für Starship, `ls`/dircolors, bat und delta,
abgeleitet aus der 42vibes-Palette (`vendor/palette.json`). Alles ist als
Kopiervorlage gedacht: dieses Repo installiert nichts global und ändert keine
Nutzer-Configs.

## Reihenfolge: Terminal-Profil zuerst

Die Farben wirken nur zusammen, wenn das Terminal-Profil die Basis setzt.
Empfohlene Reihenfolge:

1. **Terminal-Profil** (Hintergrund, Vordergrund, Cursor, Auswahl, ANSI 16)
2. **Starship** (`starship.toml`)
3. **bat** (`bat/42vibes.tmTheme`, `bat/42vibes-light.tmTheme`)
4. **delta** (`delta.gitconfig`)
5. **ls-Farben** (`dircolors.gnu` für GNU ls, `lscolors.bsd` für macOS `/bin/ls`)
6. **`palette.sh`** in eigenen Skripten

Warum zuerst das Terminal? Starship und bat sprechen Hex/Truecolor, `ls` und
delta sprechen ANSI-Namen. Wenn die ANSI-Slots im Terminal nicht zur Palette
passen, sehen dieselben Rollen in den Werkzeugen unterschiedlich aus.

## Palette

Die folgende Vorschau ist generiert: `build.py` erzeugt beide SVGs aus
`vendor/palette.json`. Es sind keine Screenshots; bitte nicht von Hand
bearbeiten.

**Dark**

![Generierte Palettenvorschau Dark: semantische Tokens und ANSI 0–15](preview/palette-dark.svg)

**Light**

![Generierte Palettenvorschau Light: semantische Tokens und ANSI 0–15](preview/palette-light.svg)

Semantische Tokens (Dark/Light):

{{SEMANTIC_TABLE}}

Die Hue-Ramps entstehen in HSL: nur die Helligkeit wandert, Farbton und
Sättigung bleiben erhalten. Die Stufen sind identisch zu den anderen
42vibes-Zielen (Dark `+0.28 … -0.38`, Light `-0.30 … +0.28`, Sättigung ×0.55
bei 100/900).

### ANSI-Reihenfolge

{{ANSI_TABLE}}

Diese 16 Werte gehören ins Terminal-Profil. `dircolors.gnu` und
`lscolors.bsd` verwenden genau diese Slots; sie können kein Hex ausgeben.

## Starship

`starship.toml` enthält zwei Paletten: `[palettes.42vibes]` (Dark, Default)
und `[palettes.42vibes_light]`. Die aktive Palette steht oben als
`palette = "42vibes"`; für hellen Hintergrund auf `42vibes_light` ändern.

Einbinden, ohne globale Config zu überschreiben:

```sh
export STARSHIP_CONFIG="$PWD/starship.toml"
# oder: cp starship.toml ~/.config/starship.toml
```

Prompt-Stil:

- Status **fett/rot**, nur bei Exit-Code != 0 (`status`, leerer
  `success_symbol`); das Character-Symbol wechselt auf das rote Fehlerzeichen.
- User/Host **gedämpft** und nur wenn relevant (`username.show_always =
  false`, `hostname.ssh_only = true`).
- Verzeichnis **fett** in Blau (`directory` → `bold interactive`).
- Git-Branch **fett** in Petrol (`git_branch` → `bold accent`).
- Kürzung: `truncation_symbol = "…/"` ist reiner Text, kein Format-String,
  und erbt den Verzeichnis-Stil; der aktuelle Ordnername bleibt fett.
- Sprach- und Tool-Versionen in Petrol, Blau oder Gold (`python`, `nodejs`,
  `rust`, `golang`, …) in der zweiten Prompt-Zeile; dort stehen auch
  kontextuelle Module wie `git_state`, `cmd_duration`, `jobs`, `package`,
  `kubernetes`, `docker_context`, `aws`, `shell` und `time`.

**Keine Nerd-Font-Pflicht:** Das Profil nutzt nur normale Unicode-Zeichen
(`❯`, `╭`, `╰`, `…`) und Textlabels wie `py`, `node`, `rs`. Wer Nerd-Font-
Symbole möchte, kann die `format`-Zeilen der Module selbst ergänzen.

## Dateifarben: GNU ls vs. macOS ls

Das sind zwei verschiedene Mechanismen – nicht verwechseln:

| | GNU ls (Linux, coreutils) | macOS `/bin/ls` (BSD) |
| --- | --- | --- |
| Variable | `LS_COLORS` | `LSCOLORS` (+ `CLICOLOR=1`) |
| Generator | `dircolors` | keiner |
| Datei hier | `dircolors.gnu` | `lscolors.bsd` |
| Umfang | 16 ANSI-Farben + beliebig viele Endungen | 11 Attributpaare, 8 Farben |
| Hex/Truecolor | nein (SGR) | nein |

### GNU ls: `dircolors.gnu`

```sh
eval "$(dircolors /pfad/zu/dircolors.gnu)"
```

Die Datei ist ein vollständiges GNU-`LS_COLORS`-Set: Standardtypen,
SUID/SGID/Sticky, Archive, Audio, Bilder, Video, Dokumente, Quellcode,
Web/Konfiguration, Build-Artefakte und Sicherungen. Diff-Dateien sind bewusst
eigene Rollen: `.diff` fett gelb, `.patch` fett cyan, `.rej` fett rot,
`.orig` gedämpft. So bleiben sie neben Grün/Rot für hinzugefügte und entfernte
Zeilen unterscheidbar.

`LEFTCODE`, `RIGHTCODE`, `ENDCODE` und `CLRTOEOL` enthalten **keine**
SGR-Zahlen, sondern Steuersequenzen (`\\e[`, `m`, `\\e[0m`, `\\e[K`), die `ls`
wörtlich um den SGR-Wert eines Eintrags schreibt. Alle anderen Werte sind
reine SGR-Sequenzen wie `01;34`. SGR-Zahlen an diesen vier Stellen landen als
Text in der Ausgabe, z.B. `0001;3401;34name00`.

Prüfen: `dircolors -b dircolors.gnu` (Exit 0).

### macOS `/bin/ls`: `lscolors.bsd`

```sh
. /pfad/zu/lscolors.bsd
```

Das Skript setzt `CLICOLOR=1` und `LSCOLORS`. **Wichtig:** macOS `ls(1)`
dokumentiert **11 Paare** – Verzeichnis, Symlink, Socket, Pipe, Executable,
Blockgerät, Zeichengerät, setuid, setgid, sticky+writable, writable. Ein
8-Paare-Wert (16 Zeichen) wird von `/bin/ls` abgelehnt; `lscolors.bsd` nutzt
daher korrekt 11 Paare (22 Zeichen).

`/bin/ls` ignoriert `LS_COLORS` vollständig. Wer auf macOS GNU ls nutzt
(Homebrew `coreutils`, Befehle `gls` und `gdircolors`), verwendet stattdessen
`dircolors.gnu`:

```sh
eval "$(gdircolors /pfad/zu/dircolors.gnu)"
alias ls='gls --color=auto'
```

## bat

```sh
mkdir -p "$(bat --config-dir)/themes"
cp bat/42vibes.tmTheme bat/42vibes-light.tmTheme "$(bat --config-dir)/themes/"
bat cache --build
export BAT_THEME=42vibes          # dunkler Hintergrund
# export BAT_THEME=42vibes-light  # heller Hintergrund
bat --list-themes | grep 42vibes
```

`bat --theme` erwartet einen Theme-**Namen**, den bat aus seinem Cache kennt,
keinen Dateipfad. Die Schritte oben (kopieren und `bat cache --build`) sind
daher erforderlich; danach funktioniert `bat --theme=42vibes datei` (oder
`BAT_THEME`).

Beide Themes sind valide tmThemes (XML/plist) mit denselben Scopes: Kommentar,
Keyword, String, Zahl, Konstante, Funktion, Typ, Variable, Operator, Markup
(heading/strong/link/quote) und `invalid`. `42vibes` nutzt die Dark-Ramps,
`42vibes-light` dieselben Ramps und Scopes auf Basis der Light-Werte.
Kommentare und Zitate sind kursiv, Überschriften und Strong fett, Links
unterstrichen. `validate.py` prüft für beide Dateien die Pflicht-Scopes und
sinnvolle Kontraste (Text/Syntax ≥ 4,5:1, Hilfsfarben ≥ 3:1).

## delta

`delta.gitconfig` ist ein Snippet, keine globale Änderung. Einbinden:

```gitconfig
[include]
    path = /pfad/zu/delta.gitconfig
```

oder pro Aufruf `git -c include.path=/pfad/zu/delta.gitconfig diff`.

Das Snippet setzt `[core] pager = delta`, `[interactive] diffFilter` und zwei
Features: `[delta "42vibes"]` (Dark, Default) und `[delta "42vibes-light"]`
(Light). Farbrollen: Blau für Datei/Pfad, Gelb/Gold für Hunk und Commit, Rot
für entfernte Zeilen und Zeilennummern, Grün für hinzugefügte Zeilen, Cyan für
neutrale Zeilennummern.

Das Light-Feature nach dem Einbinden aktivieren. Den `[include]` vor einer
eventuellen `[delta]`-Sektion platzieren, damit `features = 42vibes` aus dem
Snippet nicht gewinnt:

```sh
git config --global include.path /pfad/zu/delta.gitconfig
git config --global delta.features 42vibes-light   # hell
git config --global delta.features 42vibes          # zurück zu dunkel
```

Für einen einzelnen Aufruf: `git -c delta.features=42vibes-light diff`.

**Grenzen von Light:** `42vibes-light` nutzt ANSI-Namen, kein Hex. Die
konkreten Farben kommen daher aus den ANSI-Slots 0–15 des Terminal-Profils;
das helle Terminal-Profil verwenden. `[delta] syntax-theme = 42vibes` ist eine
Top-Level-Option, und delta bevorzugt `[delta]` gegenüber Features; das
Light-Feature kann das Syntax-Theme deshalb nicht umschalten. Für helle
Syntax-Hervorhebung `git -c delta.syntax-theme=42vibes-light diff` verwenden;
das bat-Theme muss über `bat cache --build` bekannt sein.

**Hex-Hinweis:** delta akzeptiert in neueren Versionen `#rrggbb` in
Style-Werten, ältere Versionen und Terminals ohne Truecolor aber nicht
zuverlässig. Das Snippet nutzt deshalb für beide Features ANSI-Namen. Die
passenden Hex-Werte stehen in der Palette-Tabelle; zum Testen `delta
--version` und `git diff` verwenden.

## palette.sh

POSIX-sh-kompatibel und für macOS bash 3.2 geeignet: keine Arrays, keine
Assoziativ-Arrays, keine bash-4-Features.

```sh
. /pfad/zu/palette.sh
printf '%s\\n' "$C_ACCENT" "$VIBES_BG" "$VIBES_ANSI_RED"
```

Exportiert werden:

- `VIBES_*` für Dark (Default) und `VIBES_LIGHT_*` für Light,
- `VIBES_ANSI_*` bzw. `VIBES_LIGHT_ANSI_*` für die 16 ANSI-Slots,
- kurze `C_*`-Variablen (Dark): `C_BG`, `C_TEXT`, `C_MUTED`, `C_ACCENT`,
  `C_BLUE`, `C_GOLD`, `C_ERROR`, `C_RED`, `C_GREEN`, `C_YELLOW`, …

Die Datei wird **gesourct**, nicht ausgeführt – sonst verschwinden die
Exporte mit der Subshell. Wer Escape-Sequenzen braucht, baut sie aus den
Hex-Werten selbst; `palette.sh` liefert nur Farbwerte.

## macOS-Unterschiede

- **`/bin/ls` vs. GNU ls:** macOS `/bin/ls` liest `LSCOLORS` (`lscolors.bsd`),
  GNU ls liest `LS_COLORS` (`dircolors.gnu`). `dircolors` gibt es auf macOS
  nicht; Homebrew-coreutils bringt `gdircolors` und `gls` mit.
- **bash 3.2:** `palette.sh` vermeidet Arrays und bash-4-Syntax. `source`
  funktioniert, `.` ist POSIX und ebenfalls ok.
- **Terminal.app:** kein Truecolor. Hex-Farben aus Starship/bat werden auf
  256/16 Farben abgebildet; ANSI-basierte Werkzeuge (`ls`, delta) bleiben
  exakt. Für exakte Hex-Werte iTerm2, Kitty, WezTerm oder Ghostty mit
  `COLORTERM=truecolor` verwenden.

## Fett und Truecolor

- Starship: `bold` ist ein Style-Token (`bold interactive`). Manche Terminals
  stellen „fett“ als helle Farbe statt als Schriftgewicht dar.
- bat: `fontStyle` `bold`/`italic`/`underline`; wenn die Schrift das nicht
  kann, bleibt der Text farbig, aber ohne Schnitt.
- Wenn ein Terminal kein Fett rendert, `bold` aus den Styles entfernen – die
  Rollen bleiben über Farbe und Position erkennbar.
- Truecolor: `COLORTERM=truecolor` prüfen (`printf '%s\\n' "$COLORTERM"`).
  Ohne Truecolor werden Hex-Werte approximiert.

## Farbzuordnung Starship/bat

{{MAPPING_TABLE}}

Die Tabelle zeigt die Dark-Werte. `42vibes-light.tmTheme` verwendet dieselben
Scopes mit den Light-Rampen; `validate.py` prüft die Kontraste für beide
Themes.

## Bauen und prüfen

```sh
python3 build.py          # erzeugt alle generierten Dateien neu
python3 build.py --check  # prüft, ob die eingecheckten Dateien aktuell sind
python3 validate.py       # TOML, XML, sh -n, dircolors, git config, LSCOLORS
make check                # beides
```

`build.py` ist die Quelle der Wahrheit. Farben ändern: `vendor/palette.json`
aus `../42vibes-palette` aktualisieren, dann `make build validate`.
`README.md`, `README.de.md`, `starship.toml`, `dircolors.gnu`, `lscolors.bsd`,
`bat/42vibes.tmTheme`, `bat/42vibes-light.tmTheme`, `delta.gitconfig`,
`palette.sh`, `preview/palette-dark.svg` und `preview/palette-light.svg` sind
generiert und eingecheckt.

## Struktur

```text
.
├── build.py                 # Generator (Palette -> alle Artefakte)
├── validate.py              # strukturelle und syntaktische Prüfungen
├── Makefile                 # build / validate / check
├── vendor/palette.json      # Kopie der gemeinsamen Palette
├── starship.toml            # generiert
├── dircolors.gnu            # generiert (GNU ls)
├── lscolors.bsd             # generiert (macOS /bin/ls)
├── bat/42vibes.tmTheme     # generiert (bat, Dark)
├── bat/42vibes-light.tmTheme  # generiert (bat, Light)
├── delta.gitconfig          # generiert (git/delta)
├── palette.sh               # generiert (POSIX sh)
└── preview/
    ├── palette-dark.svg     # generiert (Palettenvorschau)
    └── palette-light.svg    # generiert (Palettenvorschau)
```

## Offene Punkte

- **delta und Hex:** Das Snippet verwendet ANSI-Namen. Hex ist in neuen
  delta-Versionen möglich, aber nicht in allen Umgebungen sicher; bei Bedarf
  die Hex-Werte aus der Palette-Tabelle einsetzen und testen.
- **LSCOLORS-Paare:** Vorgabe war 8 Paare, macOS `ls(1)` verlangt 11.
  Die Datei folgt der macOS-Dokumentation; 8 Paare wären ungültig.
- **Light-Varianten:** Starship und bat haben Light-Varianten
  (`42vibes_light`, `42vibes-light.tmTheme`); delta hat das Feature
  `42vibes-light`, nutzt aber ANSI-Namen und behält ohne Override das dunkle
  Syntax-Theme (siehe delta). `dircolors.gnu` und `lscolors.bsd` sind auf den
  dunklen Hintergrund abgestimmt. Die Light-Werte stehen in der
  Palette-Tabelle für eigene Ableitungen.
- **Terminal.app:** kein Truecolor; Hex-Farben werden approximiert.
- **Nerd Font:** absichtlich keine Private-Use-Glyphen; Symbole sind optional.
- **delta `syntax-theme`:** setzt voraus, dass das bat-Theme installiert und
  mit `bat cache --build` bekannt ist.

## Lizenz

MIT, Copyright 2026 42vibes. Der vollständige Text steht in [`LICENSE`](LICENSE).
"""


def build_readme(lang: str) -> str:
    template = README_TEMPLATE_EN if lang == "en" else README_TEMPLATE_DE
    readme = template.replace("{{SEMANTIC_TABLE}}", md_semantic_table(lang))
    readme = readme.replace("{{ANSI_TABLE}}", md_ansi_table(lang))
    readme = readme.replace("{{MAPPING_TABLE}}", md_mapping_table(lang))
    return readme


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def collect() -> None:
    ARTIFACTS.clear()
    add("starship.toml", build_starship())
    add("dircolors.gnu", build_dircolors())
    add("lscolors.bsd", build_lscolors_bsd())
    for mode, name in (("dark", "42vibes"), ("light", "42vibes-light")):
        add(f"bat/{name}.tmTheme", build_tmtheme(mode, name))
    add("delta.gitconfig", build_delta())
    add("palette.sh", build_palette_sh())
    for mode in MODES:
        add(f"preview/palette-{mode}.svg", build_palette_svg(mode))
    add("README.md", build_readme("en"))
    add("README.de.md", build_readme("de"))


def main() -> int:
    check = "--check" in sys.argv[1:]
    collect()

    if check:
        stale = [
            path.relative_to(ROOT)
            for path, content in ARTIFACTS
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            for path in stale:
                print(f"veraltet: {path}")
            print("build.py --check: Dateien weichen ab, bitte 'python3 build.py' ausfuehren")
            return 1
        print(f"build.py --check: {len(ARTIFACTS)} Dateien aktuell")
        return 0

    for path, content in ARTIFACTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"geschrieben: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
