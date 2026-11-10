import sys
from pathlib import Path
from datetime import datetime, timezone
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reclaim_vm_images import removal_plan

def image(identity='old', repo='ghcr.io/syednajam01/alphazee-api', created='2026-11-08T00:00:00Z', tags=None):
    return {'Id': identity, 'RepoDigests': [repo + '@sha256:' + 'a' * 64], 'RepoTags': tags, 'Created': created}

class SafeImageSelection(unittest.TestCase):
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)

    def test_current_previous_pending_and_container_images_are_never_selected(self):
        records = [image(name) for name in ['current', 'previous', 'pending', 'container']]
        self.assertEqual(removal_plan(records, {row['Id'] for row in records}, self.now), [])

    def test_foreign_and_manually_tagged_images_are_kept(self):
        records = [image(repo='postgres'), image(tags=['manual:keep'])]
        self.assertEqual(removal_plan(records, set(), self.now), [])

    def test_recent_unknown_and_future_creation_dates_are_kept(self):
        records = [image(created='2026-11-09T23:00:00Z'), image(created='unknown'), image(created='2026-11-11T00:00:00Z')]
        self.assertEqual(removal_plan(records, set(), self.now), [])

    def test_only_old_owned_digest_references_are_selected_once(self):
        old = image()
        self.assertEqual(removal_plan([old, old], set(), self.now), old['RepoDigests'])

    def test_digest_pinned_containerd_alias_is_not_a_foreign_manual_tag(self):
        old = image()
        old['RepoTags'] = list(old['RepoDigests'])
        self.assertEqual(removal_plan([old], set(), self.now), old['RepoDigests'])
        self.assertEqual(removal_plan([old], {old['Id']}, self.now), [])
