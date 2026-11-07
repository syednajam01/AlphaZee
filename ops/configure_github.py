"""One-time settings installation. Requires a fine-grained admin token via hidden prompt.

Does not commit/push code, enable CD, or receive Azure credentials. Run after CI exists on GitHub.
"""
import getpass
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'https://api.github.com/repos/syednajam01/AlphaZee'


def main():
    token = os.environ.get('GITHUB_SETUP_TOKEN') or getpass.getpass('GitHub setup token (hidden): ')
    def api(method, path, body=None):
        request = Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Authorization':'Bearer ' + token, 'Accept':'application/vnd.github+json',
                                   'Content-Type':'application/json', 'X-GitHub-Api-Version':'2022-11-28'})
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    api('PUT', '/environments/production', {'deployment_branch_policy': {'protected_branches':False, 'custom_branch_policies':True}})
    policies = api('GET', '/environments/production/deployment-branch-policies')['branch_policies']
    for policy in policies:
        if policy['name'] != 'main' or policy.get('type', 'branch') != 'branch':
            raise RuntimeError('Review existing environment branch policies before changing them')
    if not policies:
        api('POST', '/environments/production/deployment-branch-policies', {'name':'main', 'type':'branch'})
    variables = {'PRODUCTION_DEPLOY_ENABLED':'false', 'AZURE_RESOURCE_GROUP':'alphazee-staging', 'AZURE_VM_NAME':'alphazee-vm'}
    for name, value in variables.items():
        try:
            api('PATCH', '/actions/variables/' + name, {'name':name, 'value':value})
        except HTTPError as error:
            if error.code != 404:
                raise
            api('POST', '/actions/variables', {'name':name, 'value':value})
    api('PUT', '/branches/main/protection', {
        'required_status_checks': {'strict':True, 'contexts':['ci-required']},
        'enforce_admins':True,
        'required_pull_request_reviews': {'dismiss_stale_reviews':True, 'require_code_owner_reviews':False, 'required_approving_review_count':0},
        'restrictions':None, 'allow_force_pushes':False, 'allow_deletions':False,
        'required_conversation_resolution':True})
    print('GitHub checks and environment configured. CD stays disabled until host onboarding passes.')

if __name__ == '__main__':
    try:
        main()
    except HTTPError as error:
        raise SystemExit(f'GitHub settings request failed with HTTP {error.code}; check permissions/plan. Token was not logged.')
