"""Small dependency-free policy check; actionlint additionally validates workflow syntax."""
from pathlib import Path
import re


def main():
    for path in Path('.github/workflows').glob('*.yml'):
        source = path.read_text()
        for action in re.findall(r'uses:\s*([^\s#]+)', source):
            assert action.startswith('./') or re.fullmatch(r'[^@]+@[a-f0-9]{40}', action), f'Unpinned action in {path}'
        assert 'pull_request_target' not in source
        assert 'cancel-in-progress: true' not in source
    print('PASS: immutable actions and workflow execution policy')

if __name__ == '__main__':
    main()
