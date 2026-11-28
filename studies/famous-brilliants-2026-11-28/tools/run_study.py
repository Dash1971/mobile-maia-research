"""Launch the external app-native host study without modifying app source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP = '096591bd8d42759e5a3f3a288d56d7c93245d6d1'
PLAN = '52065e0c57b788875687f41ace29cb252c92b242'
MODEL = '992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('app', 'flutter', 'stockfish', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    app, output, engine = a.app.resolve(), a.output.resolve(), a.stockfish.resolve()
    source = subprocess.check_output(['git', '-C', str(app), 'rev-parse', 'HEAD'], text=True).strip()
    if source != APP:
        p.error('Use the exact documented app pin.')
    if output.exists():
        p.error('Choose a new output path; preserve the original evidence.')
    if not (app / '.dart_tool/package_config.json').exists():
        p.error('Prepare the shared local package cache with flutter pub get --offline.')
    model = app / 'assets/classifiers/mute-exchange-model.json'
    if hashlib.sha256(model.read_bytes()).hexdigest() != MODEL:
        p.error('Classifier model checksum does not match the pin.')
    identity = subprocess.run([str(engine)], input='uci\nquit\n', text=True, capture_output=True, timeout=10, check=True).stdout
    if 'id name Stockfish 18' not in identity:
        p.error('Use Stockfish18 for this comparison.')
    output.parent.mkdir(parents=True, exist_ok=True)
    setup = output.with_suffix('.input.json')
    if setup.exists():
        p.error('Research input file already exists; choose a fresh output path.')
    data = {'appSource': APP, 'planCommit': PLAN, 'modelSource': '59cab58a8b63387d9775252f03a6875fe451f697', 'modelSha256': MODEL, 'engine': {'name': 'Stockfish18', 'binarySha256': hashlib.sha256(engine.read_bytes()).hexdigest(), 'binaryBytes': engine.stat().st_size, 'host': os.uname().sysname + ' ' + os.uname().machine}, 'games': json.loads((ROOT / 'data/games.json').read_text())}
    setup.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    env = os.environ.copy()
    env.update(BRILLY_STUDY_INPUT=str(setup), BRILLY_APP_ROOT=str(app), BRILLY_STUDY_OUTPUT=str(output), BRILLY_STOCKFISH=str(engine))
    subprocess.run([str(a.flutter.resolve()), 'test', '--no-pub', str(ROOT / 'tools/run_study_test.dart'), '--reporter', 'expanded'], cwd=app, env=env, check=True)


if __name__ == '__main__':
    main()
