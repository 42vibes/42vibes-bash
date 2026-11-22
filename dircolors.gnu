# GENERIERT von build.py aus vendor/palette.json. Nicht direkt bearbeiten.
# GNU dircolors-Format: eval "$(dircolors /pfad/zu/dircolors.gnu)"
# macOS /bin/ls nutzt LSCOLORS, nicht diese Datei; siehe lscolors.bsd.
#
# Werte: alle Eintraege sind SGR-Codes (z.B. 01;34), AUSSER
#   LEFTCODE  \e[   RIGHTCODE  m   ENDCODE  \e[0m   CLRTOEOL  \e[K
# Diese vier sind Steuersequenzen, die ls woertlich schreibt; SGR-Zahlen
# an dieser Stelle erzeugen Ausgaben wie '0001;3401;34name00'.
#
# ANSI-Zuordnung (Dark):
#   black                #0b1621  SGR 30
#   red                  #dd7a85  SGR 31
#   green                #2fb59d  SGR 32
#   yellow               #e7b45a  SGR 33
#   blue                 #55a7c8  SGR 34
#   magenta              #9d8fd8  SGR 35
#   cyan                 #4fc3c9  SGR 36
#   white                #bfcdd9  SGR 37
#   bright_black         #6b7d8e  SGR 90
#   bright_red           #f0a0a9  SGR 91
#   bright_green         #60d6c1  SGR 92
#   bright_yellow        #f1d4a1  SGR 93
#   bright_blue          #93c7dc  SGR 94
#   bright_magenta       #cbbff0  SGR 95
#   bright_cyan          #7fdde1  SGR 96
#   bright_white         #f8fafc  SGR 97

NORMAL 00
FILE 00
RESET 0
DIR 01;34
LINK 01;36
SYMLINK 01;36
FIFO 01;33
SOCK 01;35
DOOR 01;35
BLK 01;33;40
CHR 01;33;40
ORPHAN 01;31
MISSING 01;31
EXEC 01;32
LEFTCODE \e[
RIGHTCODE m
ENDCODE \e[0m
SUID 01;37;41
SGID 01;37;46
STICKY_OTHER_WRITABLE 30;42
OTHER_WRITABLE 34;42
STICKY 37;44
CAPABILITY 30;41
MULTIHARDLINK 00
CLRTOEOL \e[K

# Archive
.7z 01;31
.ar 01;31
.bz 01;31
.bz2 01;31
.cab 01;31
.cpio 01;31
.gz 01;31
.lz 01;31
.lz4 01;31
.lzh 01;31
.lzma 01;31
.rar 01;31
.tar 01;31
.tar.bz2 01;31
.tar.gz 01;31
.tar.xz 01;31
.tar.zst 01;31
.taz 01;31
.tbz 01;31
.tbz2 01;31
.tgz 01;31
.tlz 01;31
.txz 01;31
.xz 01;31
.z 01;31
.zip 01;31
.zst 01;31

# Audio
.aac 36
.aiff 36
.au 36
.flac 36
.m4a 36
.mid 36
.midi 36
.mka 36
.mp3 36
.mpc 36
.ogg 36
.opus 36
.ra 36
.wav 36
.wma 36

# Bilder
.ani 35
.avif 35
.bmp 35
.cin 35
.dds 35
.exr 35
.gif 35
.heic 35
.heif 35
.ico 35
.jpeg 35
.jpg 35
.jxl 35
.mng 35
.pbm 35
.pcx 35
.pgm 35
.png 35
.pnm 35
.ppm 35
.psd 35
.ras 35
.rgb 35
.svg 35
.tga 35
.tif 35
.tiff 35
.webp 35
.xbm 35
.xcf 35
.xpm 35
.xwd 35

# Video
.3g2 01;35
.3gp 01;35
.avi 01;35
.flv 01;35
.m2v 01;35
.m4v 01;35
.mkv 01;35
.mov 01;35
.mp4 01;35
.mpeg 01;35
.mpg 01;35
.ogm 01;35
.ogv 01;35
.qt 01;35
.rm 01;35
.rmvb 01;35
.vob 01;35
.webm 01;35
.wmv 01;35

# Dokumente
.doc 33
.docx 33
.epub 33
.mobi 33
.odp 33
.ods 33
.odt 33
.pdf 33
.ppt 33
.pptx 33
.rtf 33
.tex 33
.xls 33
.xlsx 33

# Quellcode
.awk 32
.bash 32
.c 32
.cc 32
.clj 32
.cljc 32
.cljs 32
.cmd 32
.cpp 32
.cs 32
.cxx 32
.d 32
.dart 32
.el 32
.erl 32
.ex 32
.exs 32
.fish 32
.go 32
.gradle 32
.groovy 32
.h 32
.hh 32
.hpp 32
.hrl 32
.hs 32
.hxx 32
.java 32
.jl 32
.kt 32
.kts 32
.lhs 32
.lisp 32
.lua 32
.m 32
.mm 32
.nix 32
.php 32
.pl 32
.pm 32
.ps1 32
.py 32
.r 32
.rb 32
.rs 32
.scala 32
.scm 32
.sed 32
.sh 32
.sql 32
.swift 32
.ts 32
.vim 32
.zig 32
.zsh 32

# Web und Konfiguration
.cjs 34
.conf 34
.cfg 34
.css 34
.dockerignore 34
.editorconfig 34
.env 34
.gitattributes 34
.gitconfig 34
.gitignore 34
.htm 34
.html 34
.ini 34
.js 34
.json 34
.json5 34
.jsonc 34
.jsx 34
.less 34
.lock 34
.mjs 34
.npmrc 34
.properties 34
.sass 34
.scss 34
.svelte 34
.toml 34
.tsx 34
.vue 34
.xhtml 34
.xml 34
.xsl 34
.xslt 34
.yaml 34
.yarnrc 34
.yml 34

# Diff: geaendert
.diff 01;33

# Diff: Patch
.patch 01;36

# Diff: abgelehnt
.rej 01;31

# Build-Artefakte
.a 90
.apk 90
.appimage 90
.beam 90
.bin 90
.class 90
.db 90
.dll 90
.dmg 90
.dylib 90
.ear 90
.exe 90
.hi 90
.img 90
.iso 90
.jar 90
.lib 90
.map 90
.msi 90
.o 90
.obj 90
.out 90
.pkg 90
.pyc 90
.pyo 90
.snap 90
.so 90
.sqlite 90
.sqlite3 90
.war 90
.wasm 90

# Sicherungen, Temp, Logs
.bak 90
.cache 90
.log 90
.old 90
.orig 90
.pid 90
.swo 90
.swp 90
.swn 90
.temp 90
.tmp 90
