"""Restore the 2026-11-02 PDF takeoff delivery into the project.

Copies every file under ./files back to its place in the project root. Any file
it would overwrite is first copied to <file>.pre-restore-<timestamp>.

Usage (from anywhere):  python deliveries/2026-11-02-revu-pdf-takeoff/restore.py [--dry-run]
"""
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'files'
PROJECT = HERE.parent.parent


def main() -> None:
    dry = '--dry-run' in sys.argv
    stamp = time.strftime('%Y%m%d-%H%M%S')
    count = 0
    for f in sorted(SRC.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(SRC)
        dest = PROJECT / rel
        if dest.exists() and dest.read_bytes() == f.read_bytes():
            continue
        print(('would restore ' if dry else 'restore ') + str(rel))
        count += 1
        if dry:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.copy2(dest, dest.with_name(dest.name + '.pre-restore-' + stamp))
        shutil.copy2(f, dest)
    print(f'{count} file(s) {"differ" if dry else "restored"}.')


if __name__ == '__main__':
    main()
