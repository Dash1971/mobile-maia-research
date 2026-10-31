"""Synthetic public-data checks only; no study outputs, inference or fitting."""
import copy
import csv
import gzip
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import verify_public as verifier

HERE = Path(__file__).resolve().parent
MOVES = ['f2f3', 'e7e5', 'g2g4', 'd8h4']


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


def write_table(path, rows):
    with path.open('w', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=['id', 'speed', 'prediction'])
        writer.writeheader()
        writer.writerows(rows)


def save_provenance(root, provenance):
    provenance['artifacts'] = {name: verifier.file_hash(root/name) for name in provenance['artifacts']}
    dump(root/'provenance.json', provenance)
    files = ['provenance.json']+sorted(provenance['artifacts'])
    (root/'SHA256SUMS').write_text(''.join(f'{verifier.file_hash(root/name)}  {name}\n' for name in files))


def fixture(root):
    data = root/'data'
    data.mkdir(parents=True)
    ids = ['a', 'b']+[f'h{i:02}' for i in range(50)]
    bots = [{'id': identity, 'conditioning_self': 600+20*i, 'conditioning_opponent': 600+20*i,
        'temperature_after_opening': 1., 'top_p_after_opening': 1., 'personality': {'history': False},
        'opening': {'full_moves': 5}, 'ratings': {s: {'initial_rating': 1400+10*i} for s in verifier.SPEEDS}}
        for i, identity in enumerate(ids)]
    manifest = {'existingIds': ['a', 'b'], 'trainingIds': ['a', 'b'], 'heldoutIds': ids[2:],
        'combinedRosterSha256': verifier.canonical_digest(bots), 'maximumAdmitted': 4,
        'stages': {'warmupEnd': 1, 'trainingEnd': 2, 'validationEnd': 4}}
    initial = {b['id']: {s: {'rating': b['ratings'][s]['initial_rating'], 'rd': 300,
        'games': 0, 'provisional': True} for s in verifier.SPEEDS} for b in bots}
    frozen, final = copy.deepcopy(initial), copy.deepcopy(initial)
    games = []
    rows = [('g01', 'original', 'warmup', 'a', 'b', 'blitz', '2026-10-31T00:03:00Z'),
            ('g02', 'original', 'training', 'a', 'b', 'rapid', '2026-10-31T00:04:00Z'),
            ('g03', 'original', 'validation', 'h00', 'a', 'blitz', '2026-10-31T00:05:00.106Z'),
            ('g04', 'tail', 'validation', 'h01', 'b', 'rapid', '2026-10-31T00:12:00Z')]
    acknowledgments = []
    for ordinal, (game_id, segment, stage, white, black, speed, at) in enumerate(rows, 1):
        games.append({'id': game_id, 'segment': segment, 'stage': stage, 'white': white, 'black': black,
            'speed': speed, 'admissionOrdinal': ordinal, 'admittedAtUtc': at,
            'state': 'finished', 'moves': MOVES,
            'result': {'status': 'mate', 'winner': 'black', 'plies': 4, 'ratedUpdate': True}})
        for identity in (white, black):
            final[identity][speed]['games'] += 1
            if ordinal <= 2:
                frozen[identity][speed]['games'] += 1
        path = data/'pgns'/(game_id+'.pgn')
        path.parent.mkdir(exist_ok=True)
        path.write_text('[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1\n')
        acknowledgments += [{'id': game_id, 'ply': ply, 'move': move} for ply, move in enumerate(MOVES)]
    final['h00']['blitz']['rating'] += 40
    final['h01']['rapid']['rating'] -= 30
    final['a']['blitz']['games'] += 1  # Separate unattributed public result.
    dump(data/'configurations.json', bots)
    dump(data/'manifest.json', manifest)
    dump(data/'initial.json', initial)
    dump(data/'training.json', frozen)
    dump(data/'final.json', final)
    with gzip.open(data/'games.jsonl.gz', 'wt') as target:
        target.write(''.join(json.dumps(g)+'\n' for g in games))
    (data/'acks.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in acknowledgments))
    for name, offset in [('v1', 10), ('v2', 5)]:
        write_table(data/(name+'.csv'), [{'id': b['id'], 'speed': speed,
            'prediction': b['ratings'][speed]['initial_rating']+offset} for b in bots for speed in verifier.SPEEDS])
    write_table(data/'baseline.csv', [{'id': b['id'], 'speed': speed,
        'prediction': b['ratings'][speed]['initial_rating']} for b in bots if b['id'] in manifest['heldoutIds'] for speed in verifier.SPEEDS])
    paths = {'configurations': 'data/configurations.json', 'designManifest': 'data/manifest.json',
        'initialPerfs': 'data/initial.json', 'frozenTrainingPerfs': 'data/training.json', 'finalPerfs': 'data/final.json',
        'games': 'data/games.jsonl.gz', 'primaryPredictions': 'data/v1.csv', 'secondaryPredictions': 'data/v2.csv',
        'seedBaseline': 'data/baseline.csv', 'acknowledgments': 'data/acks.jsonl'}
    provenance = {'schemaVersion': verifier.SCHEMA, 'status': 'final', 'syntheticFixture': True,
        'fullPrimaryFitArtifactIncluded': False, 'dataFiles': paths,
        'seedBaselineScope': 'heldout-native-label-only',
        'seedBaselineDefinition': 'Recorded roster ratings[speed].initial_rating for each held-out identity.',
        'expectedCounts': {'identities': 52, 'trainingIdentities': 2, 'trainingEffectiveConfigurations': 2,
            'heldoutIdentities': 50, 'heldoutEffectiveConfigurations': 50, 'crossSplitEffectiveAliases': 0},
        'sourcePins': {'originalMain': 'a'*40, 'secondaryProcedureCommit': 'b'*40,
            'continuationMain': 'e'*40,
            'maiaModelSha256': 'c'*64, 'primaryFitArtifactSha256': 'd'*64,
            'frozenTrainingSnapshotSha256': verifier.file_hash(data/'training.json')},
        'secondaryFitTrainingSnapshotSha256': verifier.file_hash(data/'training.json'),
        'predictionFreeze': {'admitted': 2, 'atUtc': '2026-10-31T00:05:00Z', 'modelSha256': 'd'*64,
            'firstHeldoutAdmissionOrdinal': 3, 'firstHeldoutAdmissionAtUtc': rows[2][-1]},
        'timingAmendment': {'authorizedAtUtc': '2026-10-31T00:01:00Z'},
        'bootstrap': {'method': 'numpy-default_rng-configuration-bootstrap', 'seed': 137,
                      'replicates': 1000, 'numpyVersion': np.__version__},
        'segments': [{'id': 'original', 'admittedAtStart': 0, 'admitted': 3, 'finished': 3, 'aborted': 0, 'unfinished': 0,
            'sourceCommit': 'a'*40,
            'startedAtUtc': '2026-10-31T00:02:00Z', 'endedAtUtc': '2026-10-31T00:10:00Z'},
            {'id': 'tail', 'admittedAtStart': 3, 'admitted': 1, 'finished': 1, 'aborted': 0, 'unfinished': 0,
            'sourceCommit': 'e'*40,
            'startedAtUtc': '2026-10-31T00:11:00Z', 'endedAtUtc': '2026-10-31T00:14:00Z'}],
        'pgnDirectory': 'data/pgns', 'artifacts': {path: '' for path in paths.values()}}
    provenance['artifacts'].update({str(p.relative_to(root)): '' for p in (data/'pgns').glob('*.pgn')})
    save_provenance(root, provenance)
    return provenance


class PublicVerifierTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE, prefix='public-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bundle = self.base/'bundle'
        self.provenance = fixture(self.bundle)

    def verify(self, **kwargs):
        return verifier.verify_bundle(self.bundle, **kwargs)

    def test_metrics_projections_and_truthful_omitted_bytes_scope(self):
        before = {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}
        metrics, receipt = self.verify()
        self.assertEqual(metrics['accounting']['admitted'], 4)
        self.assertEqual(metrics['accounting']['unattributedNativePlayerResultDelta'], 1)
        self.assertEqual(metrics['procedures']['primaryV1']['speeds']['blitz']['nativeRatingMae'], 30)
        self.assertEqual(metrics['seedBaseline']['speeds']['rapid']['nativeRatingMae'], 30)
        self.assertFalse(receipt['originalFullPrimaryArtifactBytesVerified'])
        self.assertFalse(receipt['regressionFitOrInferencePerformed'])
        self.assertEqual(receipt['acknowledgments']['uniqueAcknowledgedGamePlies'], 16)
        self.assertEqual(before, {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()})

    def test_reported_metric_comparison_and_cli(self):
        metrics, _ = self.verify()
        dump(self.bundle/'data/evaluation.json', metrics)
        self.provenance['dataFiles']['reportedEvaluation'] = 'data/evaluation.json'
        self.provenance['artifacts']['data/evaluation.json'] = ''
        save_provenance(self.bundle, self.provenance)
        self.assertTrue(self.verify(check_reported=True)[1]['reportedMetricsMatched'])
        output = self.base/'recomputed'
        result = subprocess.run([sys.executable, str(HERE/'verify_public.py'), '--bundle', str(self.bundle),
            '--output', str(output), '--check-reported'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output/'verification.json').exists())
        metrics['procedures']['primaryV1']['speeds']['blitz']['nativeRatingMae'] += 1
        dump(self.bundle/'data/evaluation.json', metrics)
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'numerical result differs'):
            self.verify(check_reported=True)

    def test_artifact_hash_change_refused(self):
        path = self.bundle/'data/v1.csv'
        path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(verifier.VerificationError, 'checksum mismatch'):
            self.verify()

    def test_duplicate_prediction_refused_even_with_fresh_hashes(self):
        path = self.bundle/'data/v1.csv'
        path.write_text(path.read_text()+path.read_text().splitlines()[1]+'\n')
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'duplicate identity/speed'):
            self.verify()

    def test_training_snapshot_cannot_be_replaced_by_final_labels(self):
        path = self.bundle/'data/training.json'
        path.write_bytes((self.bundle/'data/final.json').read_bytes())
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'training snapshot bytes differ'):
            self.verify()

    def test_native_game_count_deficit_is_refused(self):
        path = self.bundle/'data/final.json'
        final = verifier.read(path)
        final['h00']['blitz']['games'] = 0
        dump(path, final)
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'game-count deficit'):
            self.verify()

    def test_missing_prediction_is_refused(self):
        path = self.bundle/'data/v1.csv'
        path.write_text('\n'.join(path.read_text().splitlines()[:-1])+'\n')
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'missing or extra identity/speed'):
            self.verify()

    def test_changed_original_source_pin_is_refused(self):
        self.provenance['segments'][0]['sourceCommit'] = 'f'*40
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'Original segment/source pin mismatch'):
            self.verify()

    def test_wrong_baseline_or_bootstrap_are_refused(self):
        self.provenance['bootstrap']['seed'] = 1
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'bootstrap method/seed/count'):
            self.verify()

    def test_all_identity_seed_baseline_reproduces_outcome_forecasts(self):
        bots = verifier.read(self.bundle/'data/configurations.json')
        write_table(self.bundle/'data/baseline.csv', [{'id': bot['id'], 'speed': speed,
            'prediction': bot['ratings'][speed]['initial_rating']} for bot in bots for speed in verifier.SPEEDS])
        self.provenance['seedBaselineScope'] = 'all-identities-native-label-and-outcome'
        save_provenance(self.bundle, self.provenance)
        metrics, _ = self.verify()
        self.assertEqual(metrics['seedBaseline']['speeds']['blitz']['frozenOutcomeGames'], 1)
        self.assertIsNotNone(metrics['seedBaseline']['speeds']['blitz']['brier'])

    def test_model_bytes_claim_cannot_be_enabled(self):
        self.provenance['fullPrimaryFitArtifactIncluded'] = True
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'prediction tables'):
            self.verify()

    def test_draft_and_unsafe_artifact_paths_are_refused(self):
        self.provenance['status'] = 'draft'
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'method drafts are not results'):
            self.verify()
        with self.assertRaisesRegex(verifier.VerificationError, 'safe relative path'):
            verifier.safe_file(self.bundle, '../outside.json')

    def test_changed_acknowledgment_sequence_is_refused(self):
        path = self.bundle/'data/acks.jsonl'
        rows = list(verifier.read_jsonl(path))
        rows[0]['move'] = 'e2e4'
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'acknowledgment/UCI sequence mismatch'):
            self.verify()

    def test_segment_offsets_cannot_double_count_games(self):
        self.provenance['segments'][1]['admittedAtStart'] = 2
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'admission offset mismatch'):
            self.verify()

    def test_configuration_leakage_is_refused(self):
        path = self.bundle/'data/configurations.json'
        bots = verifier.read(path)
        for field in ('conditioning_self', 'conditioning_opponent'):
            bots[2][field] = bots[0][field]
        dump(path, bots)
        manifest = verifier.read(self.bundle/'data/manifest.json')
        manifest['combinedRosterSha256'] = verifier.canonical_digest(bots)
        dump(self.bundle/'data/manifest.json', manifest)
        save_provenance(self.bundle, self.provenance)
        with self.assertRaisesRegex(verifier.VerificationError, 'policy aliases/leakage'):
            self.verify()

    @unittest.skipUnless(importlib.util.find_spec('chess') is not None, 'Optional chess dependency absent')
    def test_optional_legal_public_pgn_replay(self):
        _, receipt = self.verify(verify_pgn=True)
        self.assertTrue(receipt['pgn']['legalReplay'])
        self.assertEqual(receipt['pgn']['files'], 4)

    @unittest.skipUnless(os.environ.get('MAIA_EVALUATOR_SOURCE'), 'Optional pinned evaluator source path not supplied')
    def test_synthetic_exact_metric_parity_with_pinned_evaluator(self):
        # Compile/exec avoids writing bytecode in the read-only application checkout.
        path = Path(os.environ['MAIA_EVALUATOR_SOURCE'])
        namespace = {'__name__': 'synthetic_evaluator_parity'}
        exec(compile(path.read_text(), str(path), 'exec'), namespace)
        manifest = verifier.read(self.bundle/'data/manifest.json')
        ratings = verifier.read(self.bundle/'data/final.json')
        # Nondegenerate configuration bootstrap: additional synthetic native
        # labels exercise multiple errors, RDs and resampled configurations.
        for index in range(8):
            for speed in verifier.SPEEDS:
                perf = ratings[f'h{index:02}'][speed]
                perf.update(games=7+index, rd=90+index*7)
                perf['rating'] += (index-3)*27
        games = list(verifier.read_jsonl(self.bundle/'data/games.jsonl.gz'))
        pairs = {(identity, speed) for identity in ratings for speed in verifier.SPEEDS}
        table = verifier.predictions(self.bundle/'data/v1.csv', pairs)
        model = {'version': 'strength137-ridge-rbf-v1', 'speeds': {speed: {'predictions': {
            identity: {'rating': table[(identity, speed)]} for identity in ratings}} for speed in verifier.SPEEDS}}
        source = namespace['evaluate'](model, manifest, ratings, games)
        ours = verifier.calculate_metrics(table, set(manifest['heldoutIds']), ratings, games, self.provenance['bootstrap'])
        self.assertEqual(source['speeds'], ours['speeds'])
        # Exercise a fractional draw target too, still entirely synthetic.
        draw_games = copy.deepcopy(games)
        draw_games[2]['result']['winner'] = None
        source_draw = namespace['evaluate'](model, manifest, ratings, draw_games)
        our_draw = verifier.calculate_metrics(table, set(manifest['heldoutIds']), ratings, draw_games, self.provenance['bootstrap'])
        self.assertEqual(source_draw['speeds'], our_draw['speeds'])


if __name__ == '__main__':
    unittest.main()
