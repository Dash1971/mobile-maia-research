"""Run the pinned app classifiers and export changed positions. Host tests only."""
import argparse
from pathlib import Path
import subprocess
import tempfile

SOURCE = '04e903b1e4abe635d2168d01b027ecc24f240651'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--flutter', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app = args.app.resolve()
    actual = subprocess.check_output(['git', '-C', str(app), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != SOURCE:
        parser.error(f'Check out the pinned Preview source {SOURCE}; found {actual}.')
    if not (app / '.dart_tool/package_config.json').exists():
        parser.error('Prepare the existing local package cache with flutter pub get --offline first.')
    template = Path(__file__).with_name('collect_changes_test.dart').read_text()
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    # The injected file imports the app's existing test fixture helper. Never
    # overwrite tracked tests; remove only this uniquely owned file afterwards.
    with tempfile.NamedTemporaryFile(mode='w', prefix='brilly_catalog_', suffix='_test.dart', dir=app / 'test', delete=False) as file:
        file.write(template)
        path = Path(file.name)
    try:
        subprocess.run([str(args.flutter.resolve()), 'test', '--no-pub', str(path), '--reporter', 'expanded', f'--dart-define=BRILLY_REVIEW_OUTPUT={args.output.resolve()}'], cwd=app, check=True)
    finally:
        path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
