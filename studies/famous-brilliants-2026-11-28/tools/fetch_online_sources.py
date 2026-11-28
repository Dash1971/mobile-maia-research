"""Fetch only the pinned online-study inputs into task-owned scratch (no LFS)."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Use a new task-owned scratch path; do not overwrite existing inputs.')
    rows=json.loads((ROOT/'online/source-receipts.json').read_text())
    pending=[]
    for row in rows:
        path=Path(row['path'])
        assert not path.is_absolute() and '..' not in path.parts
        assert row['url'].startswith('https://raw.githubusercontent.com/Dash1971/open-brilly-finder/59cab58a8b63387d9775252f03a6875fe451f697/')
        with urlopen(row['url'],timeout=60) as r:data=r.read(row['bytes']+1)
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],path
        pending.append((path,data))
    for path,data in pending:
        dest=a.output/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    print(f'Fetched and verified {len(rows)} ordinary Git files; no model weights or LFS downloads.')


if __name__=='__main__':main()
