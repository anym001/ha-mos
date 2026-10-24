# shellcheck shell=bash
# Formats and lints the card's Markdown in frontend/, which the blueprint's globs do not cover.
"$NPM_BIN/prettier" --write "frontend/*.md"
"$NPM_BIN/markdownlint-cli2" --fix "frontend/*.md"
