"""Regression checks for Ginger mode-counting and evidence validation."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'modes', Path(__file__).with_name('compare_ginger_modes.py'))
modes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(modes)


def run(old, new):
    def algorithm(values):
        return dict(final=[dict(ply=p, label=l) for p,l in values],
                    provisional=[dict(ply=p, label=l) for p,l in values],
                    confirmationSearches=0, confirmations={})
    return dict(old=algorithm(old), new=algorithm(new))


class CountingTest(unittest.TestCase):
    def setUp(self):
        self.game=dict(scoredPlies=[1,3,5], strictBrilliants=[dict(ply=1),dict(ply=3)])

    def test_counts_only_ginger_and_distinguishes_recovery_from_all_awards(self):
        r=run([(1,'brilliant'),(2,'brilliant'),(3,'interesting'),(5,'brilliant')],
              [(1,'brilliant'),(2,'brilliant'),(3,'brilliant'),(5,'good')])
        self.assertEqual(modes.count(self.game,r),dict(games=1,scoredMoves=3,targets=2,
            oldHits=1,newHits=2,oldAwards=2,newAwards=2,oldOutside=1,newOutside=0,
            gainedTargets=1,lostTargets=0))

    def test_losses_and_new_outside_awards_remain_visible(self):
        r=run([(1,'brilliant'),(3,'brilliant')],[(3,'brilliant'),(5,'brilliant')])
        c=modes.count(self.game,r)
        self.assertEqual((c['oldHits'],c['newHits'],c['lostTargets'],c['newOutside']),(2,1,1,1))
        self.assertEqual(c['gainedTargets'],0)

    def test_provisional_award_is_not_counted_as_final(self):
        r=run([],[(1,'interesting')])
        r['new']['provisional']=[dict(ply=1,label='brilliant')]
        self.assertEqual(modes.count(self.game,r)['newAwards'],0)

    def test_duplicate_label_rows_are_rejected(self):
        with self.assertRaises(AssertionError):
            modes.labels(run([],[(1,'brilliant'),(1,'brilliant')]),'new')


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        board=modes.chess.Board()
        initial=board.fen();board.push_uci('e2e4')
        self.game=dict(id='test', positions=[initial,board.fen()], moves=['e2e4'],sans=['e4'])
        self.run=run([],[])
        self.run.update(quality='balanced',scores=[
            dict(cp=0,mate=None,lines=[dict(cp=0,mate=None,moves=[uci])],
                 evidence=dict(quality='balanced',complete=True,depth=14))
            for uci in ['e2e4','e7e5']])

    def test_legal_complete_run_is_accepted(self):
        modes.verify_run(self.game,self.run)

    def test_illegal_pv_is_rejected(self):
        self.run['scores'][0]['lines'][0]['moves']=['c1c8']
        with self.assertRaises(AssertionError):modes.verify_run(self.game,self.run)

    def test_incomplete_or_wrong_mode_evidence_is_rejected(self):
        for field,value in [('complete',False),('quality','fast')]:
            r=copy.deepcopy(self.run);r['scores'][0]['evidence'][field]=value
            with self.assertRaises(AssertionError):modes.verify_run(self.game,r)

    def test_shallower_confirmation_is_rejected(self):
        confirmation=dict(before=copy.deepcopy(self.run['scores'][0]),after=copy.deepcopy(self.run['scores'][1]))
        confirmation['before']['evidence']['depth']=13
        self.run['new']['confirmations']={'1':confirmation}
        with self.assertRaises(AssertionError):modes.verify_run(self.game,self.run)

    def test_budget_overrun_is_rejected(self):
        self.run['new']['confirmationSearches']=7
        with self.assertRaises(AssertionError):modes.verify_run(self.game,self.run)


if __name__=='__main__':
    unittest.main()
