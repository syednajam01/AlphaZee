"""Age-based generated-file cleanup. Read-only dry run unless --apply is supplied."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.services.media import cleanup


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--minimum-age-hours', type=int, default=24)
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(cleanup(db, args.minimum_age_hours, dry_run=not args.apply), indent=2))
