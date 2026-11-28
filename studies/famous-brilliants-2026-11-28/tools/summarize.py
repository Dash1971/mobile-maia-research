"""Summarize actual completed app runs; generate the public report and viewer data."""
import argparse
import hashlib
import html
import json
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
QUALITIES = ('fast', 'balanced', 'thorough')
GRADES = {None: 'Unmarked', 'brilliant': 'Brilliant !!', 'good': 'Good !', 'interesting': 'Interesting !?', 'dubious': 'Dubious ?!', 'mistake': 'Mistake ?', 'blunder': 'Blunder ??'}
SHORT = {'opera-1858': 'Opera Game', 'byrne-fischer-1956': 'Byrne–Fischer', 'immortal-1851': 'Immortal Game', 'evergreen-1852': 'Evergreen Game', 'rotlewi-rubinstein-1907': 'Rotlewi–Rubinstein', 'levitsky-marshall-1912': 'Levitsky–Marshall', 'lasker-thomas-1912': 'Lasker–Thomas', 'kasparov-topalov-1999': 'Kasparov–Topalov', 'short-timman-1991': 'Short–Timman'}


def labelmap(algorithm, field='final'):
    return {row['ply']: row['label'] for row in algorithm[field]}


def move_label(game, ply):
    board = chess.Board(game['positions'][ply - 1])
    return str(board.fullmove_number) + ('.' if board.turn else '...') + game['sans'][ply - 1]


def pv(fen, moves):
    b = chess.Board(fen)
    out = []
    for uci in moves[:8]:
        m = chess.Move.from_uci(uci)
        assert m in b.legal_moves
        out.append((str(b.fullmove_number) + ('.' if b.turn else '...') if not out or b.turn else '') + b.san(m))
        b.push(m)
    return ' '.join(out) + (' …' if len(moves) > 8 else '')


def build(raw):
    games = json.loads((ROOT / 'data/games.json').read_text())
    assert len(raw['runs']) == 27, 'Do not publish a partial study.'
    runs = {(r['game'], r['quality']): r for r in raw['runs']}
    totals = {q: dict(oldHits=0, newHits=0, targets=0, oldAwards=0, newAwards=0, gainedTargets=0, lostTargets=0, additionalOld=0, additionalNew=0) for q in QUALITIES}
    public = []
    for game in games:
        anchors = {a['ply']: a for a in game['strictBrilliants']}
        notes = {a['ply']: a for a in game['otherAnnotations']}
        cases = set(anchors) | set(notes)
        stats = {}
        for q in QUALITIES:
            run = runs[game['id'], q]
            assert len(run['scores']) == len(game['positions'])
            maps = {k: labelmap(run[k]) for k in ('old', 'new')}
            old = {p for p, v in maps['old'].items() if v == 'brilliant'}
            new = {p for p, v in maps['new'].items() if v == 'brilliant'}
            cases |= old | new
            row = dict(targets=len(anchors), oldHits=len(old & anchors.keys()), newHits=len(new & anchors.keys()), oldAwards=len(old), newAwards=len(new), gainedTargets=len((new - old) & anchors.keys()), lostTargets=len((old - new) & anchors.keys()), additionalOld=len(old - anchors.keys()), additionalNew=len(new - anchors.keys()))
            stats[q] = row
            for key, value in row.items(): totals[q][key] += value
        entries = []
        for ply in sorted(cases):
            board = chess.Board(game['positions'][ply - 1])
            m = chess.Move.from_uci(game['moves'][ply - 1])
            assert m in board.legal_moves and board.san(m) == game['sans'][ply - 1]
            board.push(m)
            assert board.board_fen() == chess.Board(game['positions'][ply]).board_fen()
            mark = anchors.get(ply) or notes.get(ply)
            entry = {'ply': ply, 'move': move_label(game, ply), 'uci': m.uci(), 'before': game['positions'][ply - 1], 'after': game['positions'][ply], 'landmark': ply in anchors, 'sourceMark': mark.get('published') if mark else None, 'sourceListed': mark is not None, 'idea': (mark or {}).get('reason', ''), 'modes': {}}
            for q in QUALITIES:
                run = runs[game['id'], q]
                old = labelmap(run['old']).get(ply)
                new = labelmap(run['new']).get(ply)
                provisional = labelmap(run['new'], 'provisional').get(ply)
                decision = run['modelDecisions'].get(str(ply), {})
                if new == 'brilliant': reason = 'Awarded Brilliant after the app’s normal evidence checks.'
                elif new in ('blunder', 'mistake', 'dubious'): reason = 'The engine-based error grade takes precedence.'
                elif provisional == 'brilliant': reason = 'A provisional award was withheld by the app’s confirmation policy.'
                elif decision.get('candidate') is False: reason = 'No qualifying piece offer: the model’s sacrifice gate is not met.'
                elif decision.get('candidate') is True: reason = 'The model score is below its fixed Brilliant cutoff.'
                else: reason = 'This move was selected for review in another mode; a standalone model diagnostic was not recorded for this mode.'
                before, after = run['scores'][ply - 1:ply + 1]
                entry['modes'][q] = {'old': old, 'new': new, 'provisionalNew': provisional, 'candidate': decision.get('candidate'), 'score': decision.get('score'), 'reason': reason, 'depths': [s['evidence']['depth'] if s['evidence'] else 0 for s in (before, after)], 'beforeCp': before['cp'], 'beforeMate': before['mate'], 'afterCp': after['cp'], 'afterMate': after['mate'], 'beforePV': pv(entry['before'], before['lines'][0]['moves']) if before['lines'] else '', 'afterPV': pv(entry['after'], after['lines'][0]['moves']) if after['lines'] else ''}
            entries.append(entry)
        public.append({'id': game['id'], 'title': SHORT[game['id']], 'fullTitle': game['title'], 'year': game['headers']['Date'][:4], 'source': game['primaryAnnotation'], 'notes': game['notes'], 'stats': stats, 'cases': entries, 'defaultPly': game['strictBrilliants'][0]['ply']})
    assert all(t['targets'] == 14 for t in totals.values())
    assert sum(len(g['moves']) for g in games) == 492
    result = {'appSource': raw['appSource'], 'planCommit': raw['planCommit'], 'modelSource': raw['modelSource'], 'modelSha256': raw['modelSha256'], 'engine': raw['engine'], 'cutoff': raw['cutoff'], 'totalPlies': 492, 'baselinePositions': 1503, 'totals': totals, 'games': public, 'grades': {('null' if k is None else k): v for k, v in GRADES.items()}}
    (ROOT / 'data/summary.json').write_text(json.dumps({'totals': totals, 'perGame': {g['id']: g['stats'] for g in public}}, indent=2) + '\n')
    (ROOT / 'web').mkdir(exist_ok=True)
    (ROOT / 'web/results.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    return result


def report(result):
    fast = result['totals']['fast']
    lines = ['# Can an offline model spot a masterpiece?', '', 'Nine famous games. Fourteen published Brilliant landmarks. Two classifiers.', '',
             '**Release target:** Open Brilly Finder is a Preview draft aiming for Mobile Maia 2.7. This study is not an Android release qualification.', '',
             '## What the tests found', '',
             f"In Fast analysis, the previous classifier found **{fast['oldHits']}/14** frozen published!! landmarks. Open Brilly Finder found **{fast['newHits']}/14**. It recovered {fast['gainedTargets']} and lost {fast['lostTargets']} at those landmarks. These are final app awards after its normal confirmation policy, not raw model predictions.", '',
             '| Game | Published!! landmarks | Previous Fast | Open Brilly Finder Fast |', '| --- | ---: | ---: | ---: |']
    for g in result['games']:
        s = g['stats']['fast']; lines.append(f"| {g['title']} ({g['year']}) | {s['targets']} | {s['oldHits']} | {s['newHits']} |")
    lines += ['', '### All three prespecified modes', '', '| Mode | Previous landmarks | New landmarks | Previous total awards | New total awards |', '| --- | ---: | ---: | ---: | ---: |']
    for q, s in result['totals'].items(): lines.append(f"| {q.title()} | {s['oldHits']}/14 | {s['newHits']}/14 | {s['oldAwards']} | {s['newAwards']} |")
    lines += ['', 'Additional awards are listed below and in the data. A move without a recorded!! is not automatically a false positive: some are explicitly!, and the source excerpts are not exhaustive labels for every move.', '', '## Walk through the games', '']
    for g in result['games']:
        lines += [f"### {g['title']} · {g['year']}", '', f"[Chosen annotation]({g['source']['url']})", '']
        for case in [c for c in g['cases'] if c['landmark']]:
            s = case['modes']['fast']
            lines += [f"**{case['move']} — published!!**", '', case['idea'], '', f"![{g['title']} {case['move']} before and after](figures/{g['id']}-{case['ply']:03d}.png)", '', f"Fast: {GRADES[s['old']]} → {GRADES[s['new']]}. {s['reason']}", '']
        lines += ['<details>', '<summary>Awarded and source-listed moves across all modes; Fast grades shown</summary>', '', '| Move | Selected source mark | Previous Fast | New Fast |', '| --- | --- | --- | --- |']
        for c in g['cases']:
            s = c['modes']['fast']; mark = c['sourceMark'] or 'Not listed'
            lines.append(f"| {c['move']} | {mark} | {GRADES[s['old']]} | {GRADES[s['new']]} |")
        lines += ['', '</details>', '']
    lines += ['## What this can establish', '',
              'The source registry and plan were committed before fresh analysis. Both classifiers saw the same baseline Stockfish 18 output; each retained its own normal provisional/confirmation/final behavior. Every position in all nine games was evaluated in all three modes. No model weights, thresholds or app rules were changed after results.', '',
              'The nine games are deliberately famous, not a random sample. Opera and Fischer were already development examples. Training membership was not audited. Human! and!! judgments vary; this is a comparison with a fixed chosen set of annotations, not objective ground truth or a recreation of a private commercial classifier. No precision, false-positive rate or population accuracy is claimed.', '',
              'Short–Timman tests quiet brilliance, not just sacrifices. Its inclusion and any misses stay in the denominator. Immortal18.Bd6?! is retained separately as a famous but questioned sacrifice. The results include every final award, even outside the selected annotation marks.', '',
              '[Plan](PLAN.md) · [Data and reproduction](README.md) · [Full engine evidence](data/engine-runs.json) · [Viewer data](web/results.json) · [Artwork notices](THIRD_PARTY.md)', '']
    text = '\n'.join(lines)
    editorial_path = ROOT / 'data/editorial.json'
    if editorial_path.exists():
        editorial = json.loads(editorial_path.read_text())
        verdict = '## Verdict\n\n' + editorial['summary'] + '\n\n' + editorial['releaseNote'] + '\n\n'
        verdict += '\n\n'.join('**' + n['title'] + '** ' + n['text'] for n in editorial['notes']) + '\n\n'
        text = text.replace('## What the tests found\n', verdict + '## What the tests found\n')
    (ROOT / 'REPORT.md').write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--runs', type=Path, required=True); a = p.parse_args()
    raw = json.loads(a.runs.read_text())
    result = build(raw); report(result)
    print(json.dumps(result['totals'], indent=2))
