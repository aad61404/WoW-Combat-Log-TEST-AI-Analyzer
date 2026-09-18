#!/bin/bash
set -eo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
node_version="$(cat .nvmrc)"

# Login shells can select different Node installations depending on cwd.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    nvm use --silent "$node_version"
fi
if [ "$(node --version)" != "v$node_version" ]; then
    echo "Please install Node $node_version with: nvm install $node_version" >&2
    exit 1
fi

cd "$project_root/apps/web"
exec npm "$@"
