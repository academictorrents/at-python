#!/usr/bin/env bash
# Build and upload academictorrents to PyPI.
#
# Usage:
#   scripts/deploy_pypi.sh            # upload to PyPI
#   scripts/deploy_pypi.sh --test     # upload to TestPyPI to try it out
#
# Credentials: an API token from https://pypi.org/manage/account/token/
# either in ~/.pypirc or as environment variables:
#   export TWINE_USERNAME=__token__
#   export TWINE_PASSWORD=pypi-...
set -euo pipefail

cd "$(dirname "$0")/.."

REPO=pypi
INDEX_URL=https://pypi.org
if [ "${1:-}" = "--test" ]; then
    REPO=testpypi
    INDEX_URL=https://test.pypi.org
fi

VERSION=$(python -c 'exec(open("academictorrents/version.py").read()); print(__version__)')
echo "==> academictorrents $VERSION -> $REPO"

# 1. Refuse to release a dirty tree (untracked files are ignored).
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "error: uncommitted changes; commit or stash them first" >&2
    exit 1
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "master" ] && [ "$REPO" = "pypi" ]; then
    read -r -p "You are on '$BRANCH', not master. Release anyway? [y/N] " ok
    [ "$ok" = "y" ] || exit 1
fi

# 2. The version must not already exist (PyPI never allows re-uploading it).
status=$(curl -s -o /dev/null -w '%{http_code}' "$INDEX_URL/pypi/academictorrents/$VERSION/json")
if [ "$status" = "200" ]; then
    echo "error: version $VERSION is already on $REPO; bump academictorrents/version.py" >&2
    exit 1
fi

# 3. Offline tests.
python -m pip install -q --upgrade build twine pytest pytest-timeout
python -m pytest tests -q

# 4. Build a clean sdist and wheel, and check them.
rm -rf dist build ./*.egg-info
python -m build
python -m twine check --strict dist/*

# 5. Smoke-test the wheel in a throwaway venv.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python -m venv "$TMP/venv"
"$TMP/venv/bin/pip" install -q dist/*.whl
(cd "$TMP" && "$TMP/venv/bin/python" -c 'import academictorrents as at; assert at.__version__ == "'"$VERSION"'"; print("import ok", at.__version__)')
"$TMP/venv/bin/at-get" --help > /dev/null

# 6. Upload.
ls -l dist
read -r -p "Upload academictorrents $VERSION to $REPO? [y/N] " ok
[ "$ok" = "y" ] || { echo "aborted"; exit 1; }
python -m twine upload --repository "$REPO" dist/*

# 7. Tag the release (real PyPI only).
if [ "$REPO" = "pypi" ]; then
    if git rev-parse "v$VERSION" >/dev/null 2>&1; then
        echo "tag v$VERSION already exists; not tagging"
    else
        git tag -a "v$VERSION" -m "academictorrents $VERSION"
        read -r -p "Push tag v$VERSION to origin? [y/N] " ok
        [ "$ok" = "y" ] && git push origin "v$VERSION"
    fi
fi

echo "==> done: $INDEX_URL/project/academictorrents/$VERSION/"
