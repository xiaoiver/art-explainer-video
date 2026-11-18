#!/usr/bin/env python3
"""Validate and compile a new CapCut/Jianying draft from a portable JSON spec."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path, help='JSON spec; relative media paths are relative to this file')
    parser.add_argument('--out', type=Path, required=True, help='new draft directory; existing paths are never replaced')
    parser.add_argument('--capcut', default='capcut', help='capcut-cli executable')
    parser.add_argument('--check-only', action='store_true', help='validate the spec without creating a draft')
    args = parser.parse_args()
    spec_path = args.spec.expanduser().resolve()
    target = args.out.expanduser().resolve()
    if target.exists():
        parser.error(f'output already exists: {target}')
    executable = shutil.which(args.capcut)
    if not executable:
        parser.error(f'capcut-cli not found: {args.capcut}')
    try:
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        for track in spec.get('tracks', []):
            for item in track.get('items', []):
                if 'path' not in item:
                    continue
                media = Path(item['path']).expanduser()
                if not media.is_absolute():
                    media = spec_path.parent / media
                media = media.resolve()
                if not media.is_file():
                    raise FileNotFoundError(f'media not found: {media}')
                item['path'] = str(media)
        with tempfile.TemporaryDirectory(prefix='art-capcut-') as temp:
            resolved_spec = Path(temp) / 'spec.json'
            resolved_spec.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
            subprocess.run([executable, 'compile', str(resolved_spec), '--check'], check=True)
            if not args.check_only:
                subprocess.run([executable, 'compile', str(resolved_spec), '--out', str(target)], check=True)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f'compile_capcut: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
