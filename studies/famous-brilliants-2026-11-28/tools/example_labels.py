"""Reader-facing attribution and summaries; no classification is performed."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT / 'data/annotation-display.json').read_text())
OLD = 'En Croissant (adapted)'
NEW = 'Open Brilly Finder'
MODES = ('fast', 'balanced', 'thorough')


def comparison_summary(case):
    awarded = {key: [q.title() for q in MODES if case['modes'][q][key] == 'brilliant'] for key in ('old','new')}
    if len(awarded['old']) == len(awarded['new']) == 3:
        return 'Both detectors label this move Brilliant in all three modes.'
    if not awarded['old'] and not awarded['new']:
        return 'Neither detector labels this move Brilliant in any mode.'
    sentences = []
    for key, name in [('old', OLD), ('new', NEW)]:
        modes = awarded[key]
        if not modes:
            sentences.append(f'{name} does not label this move Brilliant.')
        else:
            where = 'all three modes' if len(modes) == 3 else ' and '.join(modes) + ' only'
            sentences.append(f'{name} labels it Brilliant in {where}.')
    return ' '.join(sentences)
