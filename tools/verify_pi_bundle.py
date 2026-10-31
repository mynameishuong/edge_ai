"""Verify transferred files and native score parity. Standard-library Python only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',default='pi-bundle.json')
    args=parser.parse_args()
    manifest = json.loads((ROOT/args.manifest).read_text(encoding='utf-8'))
    for name, expected in manifest['sha256'].items():
        actual = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f'File checksum mismatch: {name}')
    binary = ROOT/'build'/('ai-vids.exe' if os.name=='nt' else 'ai-vids')
    output = subprocess.check_output([str(binary), 'score', str(ROOT/'models'/'demo.forest'),
                                      str(ROOT/'models'/'pi-golden-features.csv')], text=True)
    actual = [float(v) for v in output.splitlines()]
    expected = [float(v) for v in (ROOT/'models'/'pi-golden-scores.txt').read_text().splitlines()]
    if len(actual)!=len(expected) or not actual:
        raise SystemExit('Golden score count mismatch')
    if not all(math.isfinite(v) for v in actual):
        raise SystemExit('Nonfinite score')
    error=max(abs(a-b) for a,b in zip(actual,expected))
    if error>1e-7:
        raise SystemExit(f'Cross-platform score mismatch: {error}')
    print(json.dumps({'status':'PASS', 'host':platform.system(), 'architecture':platform.machine(),
                      'files_verified':len(manifest['sha256']), 'golden_windows':len(actual),
                      'max_score_error':error,
                      'scope':'Transfer/build parity only; not detection-quality or Pi performance validation.'},indent=2))


if __name__=='__main__':
    main()
