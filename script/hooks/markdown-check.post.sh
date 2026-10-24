# shellcheck shell=bash
# Checks the card's Markdown in frontend/, which the blueprint's globs do not cover.
"$NPM_BIN/prettier" --check "frontend/*.md"
"$NPM_BIN/markdownlint-cli2" "frontend/*.md"
