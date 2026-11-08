#!/usr/bin/env bash
# Authenticated Azure Cloud Shell; existing storage account only, no account keys.
set -euo pipefail
group=alphazee-staging
vm=alphazee-vm
account=alphazeestaging
container=alphazee-backups
account_id=$(az storage account list --query "[?name=='$account'].id | [0]" -o tsv)
test -n "$account_id" || { printf 'Existing backup storage account was not found in the selected subscription.\n' >&2; exit 1; }
az vm identity assign -g "$group" -n "$vm" -o none
principal=$(az vm show -g "$group" -n "$vm" --query identity.principalId -o tsv)
test -n "$principal"
scope="$account_id/blobServices/default/containers/$container"
url="https://management.azure.com$scope?api-version=2023-05-01"
# Ensure this dedicated backup container is private through the ARM control plane.
az rest --method put --url "$url" --body '{"properties":{"publicAccess":"None"}}' -o none
count=$(az role assignment list --scope "$scope" --query "[?principalId=='$principal' && roleDefinitionName=='Storage Blob Data Contributor'] | length(@)" -o tsv)
if [ "$count" = 0 ]; then
  az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role 'Storage Blob Data Contributor' --scope "$scope" -o none
fi
printf 'PASS: VM system identity and private backup-container permission configured. Allow several minutes for propagation.\n'
