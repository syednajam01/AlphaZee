#!/usr/bin/env bash
# Cloud Shell: grant the VM identity access to an EXISTING private backup container.
set -euo pipefail
: "${BACKUP_STORAGE_ACCOUNT:?Set the existing backup storage account name}"
: "${BACKUP_RESOURCE_GROUP:?Set the storage account resource group}"
: "${BACKUP_CONTAINER:?Set the existing private container name}"
group=alphazee-staging
vm=alphazee-vm
account_id=$(az storage account show -g "$BACKUP_RESOURCE_GROUP" -n "$BACKUP_STORAGE_ACCOUNT" --query id -o tsv)
access=$(az storage container show --account-name "$BACKUP_STORAGE_ACCOUNT" --name "$BACKUP_CONTAINER" --auth-mode login --query properties.publicAccess -o tsv)
test -z "$access" || test "$access" = None || test "$access" = off
az vm identity assign -g "$group" -n "$vm" -o none
principal=$(az vm show -g "$group" -n "$vm" --query identity.principalId -o tsv)
scope="$account_id/blobServices/default/containers/$BACKUP_CONTAINER"
count=$(az role assignment list --scope "$scope" --query "[?principalId=='$principal' && roleDefinitionName=='Storage Blob Data Contributor'] | length(@)" -o tsv)
if [ "$count" = 0 ]; then
  az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role 'Storage Blob Data Contributor' --scope "$scope" -o none
fi
printf 'VM identity configured for the private backup container. Allow time for RBAC propagation.\n'
