"""Build a real C++ inference demo. All supplied CAN data is synthetic."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / 'build' / ('ai-vids.exe' if os.name == 'nt' else 'ai-vids')
FEATURES = ['fps', 'unique_ids', 'id_entropy', 'max_id_share', 'byte_mean',
            'byte_std', 'bit_flip_mean', 'same_id_iat_ms']


def build():
    BIN.parent.mkdir(exist_ok=True)
    source = ROOT / 'src' / 'main.cpp'
    compiler = shutil.which('g++') or shutil.which('clang++')
    command = [compiler] if compiler else [sys.executable, '-m', 'ziglang', 'c++']
    with (BIN.parent/'build.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command + ['-std=c++17', '-O2', '-Wall', '-Wextra',
                                str(source), '-o', str(BIN)], cwd=ROOT, stdout=log, stderr=log)
    if result.returncode:
        raise RuntimeError('C++ build failed; see build/build.log')


def generate(path: Path, seconds: int, seed: int, attacks=False):
    rng = random.Random(seed)
    # Three simulated ECUs; no OEM signal definitions or real vehicle payloads.
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp_us', 'can_id_hex', 'dlc', 'data_hex', 'label'])
        for w in range(seconds * 10 + 1):
            t = w / 10
            scenario = ('flooding' if 8 <= t < 12 else
                        'unknown_id' if 18 <= t < 22 else
                        'payload_shift' if 28 <= t < 32 else
                        'silence' if 38 <= t < 40 else 'normal') if attacks else 'normal'
            if scenario == 'silence':
                continue
            n = rng.randint(85, 105) if scenario != 'flooding' else rng.randint(260, 300)
            for j in range(n):
                ts = w * 100000 + j * 100000 // n
                canid = [0x100, 0x200, 0x300][j % 3]
                if scenario == 'unknown_id' and j % 3 == 0:
                    canid = 0x666
                # Smooth toy signals plus small independent noise.
                value = 80 + 15 * math.sin(ts / 3e6)
                payload = bytes(max(0, min(255, round(value + k * 8 + rng.gauss(0, 5)))) for k in range(8))
                if scenario == 'payload_shift':
                    payload = bytes(rng.randint(220, 255) for _ in range(8))
                writer.writerow([ts, f'{canid:03X}', 8, payload.hex().upper(), scenario])


def extract(source, target):
    subprocess.run([str(BIN), 'features', str(source), str(target)], check=True)


def main():
    import numpy as np
    import sklearn
    from sklearn.ensemble import IsolationForest

    for folder in ['data', 'models', 'runtime', 'build']:
        (ROOT / folder).mkdir(exist_ok=True)
    print('Building C++17 engine...', flush=True)
    build()
    print('Generating separate synthetic train / validation / test sessions...', flush=True)
    for name, seconds, seed in [('train', 120, 41), ('validation', 60, 72), ('normal_test', 60, 93), ('demo', 46, 119)]:
        generate(ROOT / 'data' / f'{name}.csv', seconds, seed, attacks=name == 'demo')
        extract(ROOT / 'data' / f'{name}.csv', ROOT / 'data' / f'{name}_features.csv')
    def load(name):
        return np.loadtxt(ROOT / 'data' / f'{name}_features.csv', delimiter=',', skiprows=1)[:, 1:].astype(np.float32)
    train, val, normal, demo = [load(s) for s in ['train', 'validation', 'normal_test', 'demo']]
    model = IsolationForest(n_estimators=64, max_samples=128, max_features=1.0,
                            contamination='auto', random_state=42, n_jobs=1).fit(train)
    # Larger positive score is more anomalous. Calibrate on held-out NORMAL only.
    threshold = float(np.quantile(-model.score_samples(val), 0.995))
    artifact = ROOT / 'models' / 'demo.forest'
    with artifact.open('w', encoding='ascii', newline='\n') as out:
        out.write(f'AIVIDS_IFOREST_V1 8 64 {model.max_samples_} {threshold:.17g} 100000 3\n')
        out.write('256 512 768\n')
        for estimator in model.estimators_:
            tree = estimator.tree_
            out.write(f'{tree.node_count}\n')
            for i in range(tree.node_count):
                out.write(f'{tree.children_left[i]} {tree.children_right[i]} {tree.feature[i]} {tree.threshold[i]:.17g} {tree.n_node_samples[i]}\n')
    # Test exported-tree scoring against sklearn on held-out and attacked data.
    errors = []
    for name, x in [('validation', val), ('normal_test', normal), ('demo', demo)]:
        output = subprocess.check_output([str(BIN), 'score', str(artifact), str(ROOT/'data'/f'{name}_features.csv')], text=True)
        cpp = np.fromstring(output, sep='\n')
        expected = -model.score_samples(x)
        error = float(np.max(np.abs(cpp-expected)))
        if error > 1e-7:
            raise RuntimeError(f'Python/C++ score parity failed: {name} {error}')
        errors.append(error)
    report = {
        'status': 'LOCAL_SYNTHETIC_ONLY', 'runtime': 'C++17 native on local PC',
        'training': 'scikit-learn IsolationForest; normal sessions only',
        'sklearn_version': sklearn.__version__, 'numpy_version': np.__version__,
        'window_us': 100000, 'window_policy': 'tumbling; final partial window omitted',
        'features': FEATURES, 'threshold': threshold,
        'threshold_calibration': '99.5 percentile of held-out normal validation scores',
        'train_windows': len(train), 'validation_windows': len(val),
        'normal_test_windows': len(normal), 'parity_windows': len(val)+len(normal)+len(demo),
        'max_score_parity_error': max(errors),
        'normal_test_ml_window_fpr': float(np.mean(-model.score_samples(normal) > threshold)),
        'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'pi_benchmark': 'NOT RUN', 'real_dataset_evaluation': 'NOT RUN',
        'note': 'Synthetic smoke test; these metrics do not estimate real-vehicle detection quality.'
    }
    (ROOT/'models'/'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (ROOT/'runtime'/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
