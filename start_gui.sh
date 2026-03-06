#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "start_gui.sh is deprecated. Launching the supported local web app instead."
exec "${ROOT_DIR}/start_local.sh"
