#!/usr/bin/env bash
# Run once in authenticated Azure Cloud Shell. No app containers/data are changed.
set -euo pipefail
group=alphazee-staging
vm=alphazee-vm
identity=alphazee-github-deploy
subscription=$(az account show --query id -o tsv)
vm_id=$(az vm show -g "$group" -n "$vm" --query id -o tsv)
az identity create -g "$group" -n "$identity" -o none
principal=$(az identity show -g "$group" -n "$identity" --query principalId -o tsv)
client=$(az identity show -g "$group" -n "$identity" --query clientId -o tsv)
tenant=$(az account show --query tenantId -o tsv)
if ! az identity federated-credential show -g "$group" --identity-name "$identity" --name github-production -o none 2>/dev/null; then
  az identity federated-credential create -g "$group" --identity-name "$identity" --name github-production \
    --issuer https://token.actions.githubusercontent.com \
    --subject repo:syednajam01/AlphaZee:environment:production \
    --audiences api://AzureADTokenExchange -o none
fi
role_file=$(mktemp)
trap 'rm -f "$role_file"' EXIT
cat > "$role_file" <<EOF
{"Name":"AlphaZee VM deployment","IsCustom":true,"Description":"Run trusted GitHub main releases on the AlphaZee VM", "Actions":["Microsoft.Compute/virtualMachines/read","Microsoft.Compute/virtualMachines/runCommand/action"],"NotActions":[],"AssignableScopes":["/subscriptions/$subscription/resourceGroups/$group"]}
EOF
if ! az role definition list --name 'AlphaZee VM deployment' --query '[0].id' -o tsv | grep -q .; then
  az role definition create --role-definition "$role_file" -o none
fi
count=$(az role assignment list --scope "$vm_id" --query "[?principalId=='$principal' && roleDefinitionName=='AlphaZee VM deployment'] | length(@)" -o tsv)
if [ "$count" = 0 ]; then
  az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role 'AlphaZee VM deployment' --scope "$vm_id" -o none
fi
printf 'Set these production-environment GitHub secrets (identifiers, not passwords):\nAZURE_CLIENT_ID=%s\nAZURE_TENANT_ID=%s\nAZURE_SUBSCRIPTION_ID=%s\n' "$client" "$tenant" "$subscription"
printf 'Next: inspect VM storage, configure private off-host backup access, and install /etc/alphazee-cicd.json. Do not enable CD yet.\n'
