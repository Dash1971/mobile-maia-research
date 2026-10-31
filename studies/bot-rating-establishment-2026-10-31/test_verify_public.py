"""Public-data verification regressions; no private evidence, fitting or inference."""
import gzip
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_public as verifier

HERE=Path(__file__).resolve().parent
BUNDLE=Path(os.environ.get('NIGHT163_PUBLIC_FIXTURE',HERE if (HERE/'data').is_dir() else HERE/'export-final-v1'))


class PublicVerificationTest(unittest.TestCase):
    def alter(self,name,transform,compressed=False):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'bundle';shutil.copytree(BUNDLE,root)
        path=root/name
        if compressed:
            with gzip.open(path,'rt') as stream: value=[json.loads(line) for line in stream]
            transform(value)
            with gzip.open(path,'wt') as stream:
                for row in value:stream.write(json.dumps(row)+'\n')
        else:
            value=json.loads(path.read_text());transform(value);path.write_text(json.dumps(value))
        lineage=verifier.read(root/'data/integrity-lineage.json')
        lineage['artifacts'][name]=verifier.sha(path)
        (root/'data/integrity-lineage.json').write_text(json.dumps(lineage))
        return root

    def test_complete_public_bundle_replays_all_games_without_fit(self):
        report=verifier.verify(BUNDLE)
        self.assertEqual(report['finishedRatedGames'],826)
        self.assertEqual(report['uniqueVerifiedPlies'],71287)
        self.assertEqual(report['finalNonprovisional'],{'blitz':250,'rapid':250})
        self.assertFalse(report['fitOrInferencePerformed'])

    def test_duplicate_ack_rejected_even_after_rehashing_public_projection(self):
        root=self.alter('data/acknowledged-moves.jsonl.gz',lambda rows:rows.append(dict(rows[0])),True)
        with self.assertRaisesRegex(ValueError,'Duplicate acknowledged'):verifier.verify(root)

    def test_policy_change_rejected_even_after_rehashing_public_projection(self):
        def change(rows):rows[0]['policies']['white']['production']['temperature']=0.123456789
        root=self.alter('data/games.jsonl.gz',change,True)
        with self.assertRaisesRegex(ValueError,'Fixed production settings'):verifier.verify(root)

    def test_undrained_training_finish_rejected_before_heldout(self):
        freeze=verifier.read(BUNDLE/'data/integrity-lineage.json')['freeze']['eventIndex']
        def change(rows):rows[0]['finishEventIndex']=freeze+1
        root=self.alter('data/games.jsonl.gz',change,True)
        with self.assertRaisesRegex(ValueError,'fully finished/drained'):verifier.verify(root)

    def test_native_count_change_rejected_even_after_rehashing_public_projection(self):
        def change(values):next(iter(values.values()))['blitz']['games']+=1
        root=self.alter('data/final-native-perfs.json',change)
        with self.assertRaisesRegex(ValueError,'Native final count delta'):verifier.verify(root)

    def test_exact_rd110_remains_native_provisional(self):
        values={'bot':{speed:{'rating':1500,'rd':110,'volatility':.09,'games':100,'provisional':True}
            for speed in verifier.SPEEDS}}
        verifier.perfs(values,{'bot'})
        values['bot']['rapid']['provisional']=False
        with self.assertRaisesRegex(ValueError,'flag/RD boundary'):verifier.perfs(values,{'bot'})

    def test_illegal_pgn_mainline_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'illegal.pgn'
            path.write_text('[Site "https://mutechess.org/game/test0001"]\n[White "Alpha"]\n[Black "Beta"]\n'
                '[WhiteTitle "BOT"]\n[BlackTitle "BOT"]\n[Result "0-1"]\n[TimeControl "300+3"]\n\n1. f3 e5 2. g5 Qh4# 0-1\n')
            game={'id':'test0001','white':'a','black':'b','speed':'blitz',
                'result':{'winner':'black','status':'mate','plies':4}}
            with self.assertRaisesRegex(ValueError,'Invalid or illegal PGN'):
                verifier.replay(path,game,{'a':{'username':'Alpha'},'b':{'username':'Beta'}})


if __name__=='__main__':unittest.main()
