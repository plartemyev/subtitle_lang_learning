#!/bin/sh
# Compile the committed .po catalogs into the .mo binaries that the app loads
# at runtime (requires the gettext toolchain; end users do NOT need it -
# the compiled .mo files are committed to the repository).
# Run this after editing any locales/*/LC_MESSAGES/messages.po, then commit
# both the .po and the regenerated .mo.
set -eu
cd "$(dirname "$0")/.."
for po in locales/*/LC_MESSAGES/messages.po; do
    msgfmt --check -o "${po%.po}.mo" "$po"
    echo "compiled $po"
done
