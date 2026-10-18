#!/usr/bin/env python3
"""Wait for the fixed data collection, then run dependent diagnostics/audits.

This supervisor never changes the sample size or retries a study with new seeds.
It is a convenience for a long local run, not an external scheduled service.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def counts():
    return {mode: sum(sum(1 for _ in p.open()) for p in (HERE / 'data').glob(mode + '-*.jsonl'))
            for mode in ('matches', 'openings')}


def command(args, name, logdir):
    with (logdir / (name + '.log')).open('w') as log:
        subprocess.run(args, cwd=HERE, stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--stockfish', required=True)
    ap.add_argument('--dart', required=True)
    ap.add_argument('--packages', required=True)
    args = ap.parse_args()
    quality = None
    last = None
    # Logs can contain machine paths from third-party libraries; keep them
    # outside the publication tree. The evidence receipts have no such paths.
    with tempfile.TemporaryDirectory(prefix='maia-opening-pipeline-') as temp:
        logdir = Path(temp)
        with (logdir / 'quality.log').open('w') as quality_log:
            while True:
                state = counts()
                if state != last:
                    print(json.dumps({'collection': state, 'target': {'matches': 3000, 'openings': 5400}}), flush=True)
                    last = state
                if state['matches'] == 3000 and quality is None:
                    quality = subprocess.Popen([sys.executable, str(HERE / 'quality.py'),
                                                '--model', args.model, '--stockfish', args.stockfish,
                                                '--workers', '2'], cwd=HERE,
                                               stdout=quality_log, stderr=subprocess.STDOUT)
                    print('Started the fixed 180-position quality diagnostic.', flush=True)
                if quality is not None and quality.poll() is not None:
                    if quality.returncode:
                        raise RuntimeError('Quality diagnostic failed; inspect local log before continuing')
                receipts = list((HERE / 'data').glob('*.receipt.json'))
                if state == {'matches': 3000, 'openings': 5400} and len(receipts) == 84:
                    break
                time.sleep(30)
            assert quality is not None
            assert quality.wait() == 0
        print('Collection and diagnostics complete; regenerating results.', flush=True)
        command([sys.executable, str(HERE / 'analyze.py')], 'analysis', logdir)
        print('Python legal-game replay and summaries passed.', flush=True)
        files = sorted((HERE / 'data').glob('matches-*.jsonl')) + sorted((HERE / 'data').glob('openings-*.jsonl'))
        with (HERE / 'verification/dart-game-replay.json').open('w') as output:
            subprocess.run([args.dart, '--packages=' + args.packages,
                            str(HERE / 'verify_dart_games.dart'), *map(str, files)],
                           stdout=output, check=True, cwd=HERE)
        print('Independent app-library replay passed.', flush=True)
        command([sys.executable, str(HERE / 'verify_cached.py')], 'cached-audit', logdir)
        print('Independent cached statistics audit passed. PIPELINE COMPLETE', flush=True)


if __name__ == '__main__':
    main()
