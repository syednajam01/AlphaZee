#!/usr/bin/env bash
# Run on the Ubuntu/Debian AlphaZee VM as root. Does not restart app containers.
set -euo pipefail
test "$(id -u)" = 0
for tool in python3 docker tar du curl; do command -v "$tool" >/dev/null; done
python3 -c 'import json; c=json.load(open("/etc/alphazee-cicd.json")); assert c["project"]=="alphazee-prod" and c["domain"]=="alphazee.tech"'
if ! command -v az >/dev/null; then
  install -d -m 700 /var/lib/alphazee-cicd
  installer=$(mktemp)
  trap 'rm -f "$installer"' EXIT
  curl --fail --silent --show-error --location 'https://azurecliprod.blob.core.windows.net/$root/deb_install.sh' -o "$installer"
  export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
  umask 077
  bash "$installer" > /var/lib/alphazee-cicd/azure-cli-install.log 2>&1
fi
az version --query '"azure-cli"' -o tsv
printf 'PASS: Azure CLI installed; application containers were not restarted.\n'
