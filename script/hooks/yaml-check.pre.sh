# shellcheck shell=bash
# Cloud sessions reach GitHub only through a proxy that rejects zizmor's online audits with 401; CI still runs them.
if [[ -n ${CLAUDE_CODE_REMOTE:-} ]]; then
    export ZIZMOR_OFFLINE=true
fi
