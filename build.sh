#!/bin/bash
# Wraps the artifact source (head fragment + body markup) into a standalone
# page for GitHub Pages, which needs the doctype/viewport the artifact host
# would otherwise supply.
set -e
SRC="${1:?usage: build.sh <source.html>}"
OUT="$(dirname "$0")/index.html"

python3 - "$SRC" "$OUT" <<'PY'
import sys
src, out = sys.argv[1], sys.argv[2]
doc = open(src, encoding="utf-8").read()
head, body = doc.split("</style>", 1)
open(out, "w", encoding="utf-8").write(
    '<!doctype html>\n<html lang="tr">\n<head>\n'
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    '<meta name="theme-color" content="#14181b">\n'
    '<style>:root{color-scheme:dark}html,body{margin:0}img{max-width:100%}'
    '[hidden]{display:none!important}</style>\n'
    + head + "</style>\n</head>\n<body>\n" + body + "\n</body>\n</html>\n"
)
PY

echo "built $OUT"
