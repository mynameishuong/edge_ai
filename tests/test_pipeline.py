from __future__ import annotations
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT/'build'/('ai-vids.exe' if os.name == 'nt' else 'ai-vids')
MODEL = ROOT/'models'/'demo.forest'
HEADER = 'timestamp_us,can_id_hex,dlc,data_hex,label\n'


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def run_frames(self, rows, mode='replay'):
        source = self.folder/'frames.csv'
        source.write_text(HEADER + rows, encoding='utf-8')
        output = self.folder/'features.csv'
        args = ['features', str(source), str(output)] if mode == 'features' else ['replay', str(source), str(MODEL)]
        proc = subprocess.run([str(BIN)] + args, capture_output=True, text=True)
        return proc, output

    def test_golden_features_and_exact_window_boundary(self):
        proc, out = self.run_frames('0,100,1,00,normal\n10000,100,1,FF,normal\n100000,200,1,01,normal\n', 'features')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = list(csv.DictReader(io.StringIO(out.read_text())))
        self.assertEqual(len(rows), 1)  # partial final window is not emitted
        expected = {'fps': 20, 'unique_ids': 1, 'id_entropy': 0, 'max_id_share': 1,
                    'byte_mean': 127.5, 'byte_std': 127.5, 'bit_flip_mean': 1,
                    'same_id_iat_ms': 10}
        for name, value in expected.items():
            self.assertAlmostEqual(float(rows[0][name]), value, places=6)

    def test_silent_gap_emits_no_data(self):
        proc, _ = self.run_frames('0,100,1,00,normal\n300000,100,1,00,normal\n')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([x['t_ms'] for x in rows], [0, 100, 200])
        self.assertEqual([x['state'] for x in rows[1:]], ['NO_DATA', 'NO_DATA'])

    def test_label_is_not_used_for_inference(self):
        rows = '0,100,1,00,normal\n10000,100,1,FF,normal\n100000,200,1,01,normal\n'
        a, _ = self.run_frames(rows)
        b, _ = self.run_frames(rows.replace('normal', 'attack'))
        for text in (a.stdout, b.stdout):
            self.assertTrue(text)
        x, y = json.loads(a.stdout), json.loads(b.stdout)
        x.pop('inference_us');y.pop('inference_us')
        self.assertEqual(x, y)

    def test_malformed_dlc_is_rejected(self):
        proc, _ = self.run_frames('0,100,8,00,normal\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('DLC/payload mismatch', proc.stderr)

    def test_out_of_order_timestamp_is_rejected(self):
        proc, _ = self.run_frames('100,100,1,00,normal\n90,100,1,00,normal\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('nondecreasing', proc.stderr)

    def test_negative_timestamp_is_rejected(self):
        proc, _ = self.run_frames('-1,100,1,00,normal\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('unsigned integer', proc.stderr)

    def test_extended_id_is_rejected(self):
        proc, _ = self.run_frames('0,123456,1,00,normal\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('11-bit', proc.stderr)

    def test_empty_payload_is_valid(self):
        proc, _ = self.run_frames('0,100,0,,normal\n100000,100,0,,normal\n')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['frames'], 1)

    def test_wrong_model_schema_is_rejected(self):
        bad = self.folder/'bad.forest';bad.write_text('WRONG 8 1 128 0.5 100000 3\n')
        proc = subprocess.run([str(BIN), 'replay', str(ROOT/'data'/'demo.csv'), str(bad)], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('schema invalid', proc.stderr)

    def test_synthetic_scenarios_have_evidence(self):
        proc = subprocess.run([str(BIN), 'replay', str(ROOT/'data'/'demo.csv'), str(MODEL)], capture_output=True, text=True, check=True)
        events = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(events), 460)
        for start, stop, reason in [(8000,12000,'possible_flooding'), (18000,22000,'unknown_id'),
                                     (28000,32000,'ml_anomaly'), (38000,40000,'no_frames')]:
            subset = [e for e in events if start <= e['t_ms'] < stop]
            self.assertTrue(subset)
            self.assertTrue(any(e['reason']==reason for e in subset), (start, reason))
        # Check alert latching on recovery after the hard-rule flooding interval.
        recovery = [e for e in events if 12000 <= e['t_ms'] < 12500]
        if all(e['reason']=='normal' for e in recovery):
            self.assertEqual([e['state'] for e in recovery], ['ALERT']*4+['HEALTHY'])

    def test_export_parity_report(self):
        report = json.loads((ROOT/'runtime'/'validation.json').read_text())
        self.assertGreaterEqual(report['parity_windows'], 1000)
        self.assertLessEqual(report['max_score_parity_error'], 1e-7)

    def test_realtime_replay_waits_until_window_end(self):
        self.run_frames('0,100,1,00,normal\n100000,100,1,01,normal\n')
        before=time.monotonic()
        proc=subprocess.run([str(BIN),'replay',str(self.folder/'frames.csv'),str(MODEL),'--realtime'],
                            capture_output=True,text=True,check=True)
        elapsed=time.monotonic()-before
        event=json.loads(proc.stdout)
        self.assertEqual(event['window_end_ms'],100)
        self.assertGreaterEqual(elapsed,.08)


if __name__ == '__main__':
    unittest.main()
