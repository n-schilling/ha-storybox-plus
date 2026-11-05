#!/bin/bash
# Runs locally what the CI workflow runs, so a push only confirms what already
# passed here: ruff, the changelog and translation checks, mypy, the tests with
# their coverage threshold, and hassfest in the very container the GitHub
# action starts. Keep the steps in step with .github/workflows/ci.yaml.
#
# Usage: scripts/check.sh [--no-hassfest]
#
# Hassfest needs Docker. Its image exists for amd64 only; on Apple silicon
# Docker runs it emulated, which takes about 20 seconds. The image is pulled
# once and then reused; `docker pull ghcr.io/home-assistant/hassfest` refreshes
# it, and the weekly CI run catches a Home Assistant change in the meantime.
set -uo pipefail
cd "$(dirname "$0")/.."

VENV=.venv/bin
if [[ ! -x "$VENV/ruff" || ! -x "$VENV/mypy" || ! -x "$VENV/pytest" ]]; then
    echo "No test environment in .venv; see README, section Development." >&2
    exit 2
fi

failed=()
skipped=()

run() { # run <name> <command...>
    local name=$1
    shift
    echo "==> $name"
    if "$@"; then
        echo "    ok: $name"
    else
        echo "    FAILED: $name"
        failed+=("$name")
    fi
    echo
}

run "Ruff check" "$VENV/ruff" check .
run "Ruff format" "$VENV/ruff" format --check .
run "Changelog has the version" bash -c \
    '.github/scripts/changelog-section.sh CHANGELOG.md "$(jq -r .version custom_components/storybox_plus/manifest.json)" > /dev/null'
run "Translations match strings.json" \
    diff custom_components/storybox_plus/strings.json custom_components/storybox_plus/translations/en.json
run "Strict typing" "$VENV/mypy" custom_components
run "Tests" "$VENV/pytest" -q \
    --cov=custom_components.storybox_plus --cov-report=term-missing:skip-covered --cov-fail-under=95

if [[ "${1:-}" == "--no-hassfest" ]]; then
    skipped+=("Hassfest (--no-hassfest)")
elif ! docker info > /dev/null 2>&1; then
    skipped+=("Hassfest (Docker is not running)")
else
    run "Hassfest" docker run --rm --platform linux/amd64 \
        -v "$PWD":/github/workspace:ro ghcr.io/home-assistant/hassfest
fi

echo "===================="
# The ${arr[@]+"${arr[@]}"} form keeps an empty array from tripping `set -u` in the bash 3.2 of macOS
for name in ${skipped[@]+"${skipped[@]}"}; do
    echo "skipped: $name"
done
if ((${#failed[@]})); then
    echo "FAILED: ${failed[*]}"
    exit 1
fi
echo "All checks passed."
