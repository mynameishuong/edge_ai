"""Create a local Pi/Ubuntu VM review bundle; never contacts the target."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',choices=['pi','ubuntu-vm'],default='pi')
    args=parser.parse_args()
    binary=ROOT/'build'/('ai-vids.exe' if os.name=='nt' else 'ai-vids')
    source=ROOT/'data'/'normal_test_features.csv'
    golden=ROOT/'models'/'pi-golden-features.csv'
    lines=source.read_text(encoding='utf-8').splitlines()
    golden.write_text('\n'.join(lines[:33])+'\n',encoding='ascii')
    output=subprocess.check_output([str(binary),'score',str(ROOT/'models'/'demo.forest'),str(golden)],text=True)
    (ROOT/'models'/'pi-golden-scores.txt').write_text(output,encoding='ascii')
    files=['CMakeLists.txt','src/main.cpp','models/demo.forest','models/manifest.json',
           'models/pi-golden-features.csv','models/pi-golden-scores.txt','data/demo.csv',
           'tools/verify_pi_bundle.py','tools/serve.py','tests/test_pipeline.py',
           'ui/index.html','docs/architecture.svg','docs/DEPLOY_RASPBERRY_PI.vi.md',
           'runtime/validation.json','docs/TASK_REVIEW.html','docs/TASK_BREAKDOWN.vi.md',
           'docs/REVIEW_PLAN.json']
    if args.target=='ubuntu-vm':
        files.append('docs/UBUNTU_VM_FIRST_RUN.vi.md')
    checksums={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
    runtime=('Build C++ natively on Linux ARM64' if args.target=='pi' else
             'Build C++ natively inside Ubuntu VM; verifier reports actual architecture')
    manifest={'purpose':'REVIEW / STAGING ONLY', 'runtime':runtime,
              'target':args.target,
              'model':'SYNTHETIC DEMO ONLY',
              'golden_reference':'32 local C++ scores; exported scorer previously checked against sklearn on 1660 windows',
              'sha256':checksums}
    manifest_name='pi-bundle.json' if args.target=='pi' else 'vm-bundle.json'
    (ROOT/manifest_name).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive_name='ai-vids-pi-review.tar.gz' if args.target=='pi' else 'ai-vids-ubuntu-vm-review.tar.gz'
    archive=ROOT/'build'/archive_name
    with tarfile.open(archive,'w:gz') as tar:
        for name in files+[manifest_name]:
            tar.add(ROOT/name,arcname=name,recursive=False)
    print(f'{archive.name}: {archive.stat().st_size:,} bytes; {len(files)+1} files; no PC binary or virtualenv')


if __name__=='__main__':
    main()
