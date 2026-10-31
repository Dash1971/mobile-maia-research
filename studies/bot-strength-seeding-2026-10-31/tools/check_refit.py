#!/usr/bin/env python3
"""Reexecute both pinned training procedures, checking published prediction tables.

Reads only the original training snapshot, roster, split and reference tables.
Does not read final ratings/outcomes, select on test results, write coefficients,
load neural weights, contact a service, or change public ratings. Small numerical
differences across linear-algebra providers are explicitly bounded and reported.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.bundle.resolve()
    assert not args.output.exists(), 'Use a new result path'
    read=lambda name:json.loads((root/'data'/name).read_text())
    roster=read('configurations.json');manifest=read('design-manifest.json');training=read('frozen-training-perfs.json')
    expected='4a88c1dd54420b81237f4323b52f328330bd46494866bc890daf9581522fe436'
    assert hashlib.sha256((root/'data/frozen-training-perfs.json').read_bytes()).hexdigest()==expected
    report={'trainingSnapshotSha256':expected,'heldoutOutcomesRead':False,
            'fittedCoefficientsWritten':False,'neuralInferencePerformed':False,'procedures':{}}
    for version in ('v1','v2'):
        source=root/'tools'/('predictor_'+version+'.py')
        spec=importlib.util.spec_from_file_location('reproduction_'+version,source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fitted=module.fit(roster,manifest,training)
        # Reference comparisons happen after the frozen procedure has finished.
        with (root/'data'/('frozen-predictions-'+version+'.csv')).open() as stream:
            reference={(r['id'],r['speed']):float(r['prediction']) for r in csv.DictReader(stream)}
        expected_keys={(b['id'],speed) for b in roster for speed in ('blitz','rapid')}
        assert set(reference)==expected_keys
        delta=max(abs(fitted['speeds'][speed]['predictions'][identity]['rating']-value)
                  for (identity,speed),value in reference.items())
        assert delta<=1e-7, 'Prediction reproduction differs: inspect the pinned numerical environment; never overwrite frozen predictions'
        report['numpyVersion']=module.np.__version__
        report['procedures'][version]={'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'modelVersion':fitted['version'],'maximumAbsolutePredictionDifference':delta,
            'predictionTolerance':1e-7,'selection':{speed:{key:fitted['speeds'][speed][key]
                for key in ('complexity','penalty','configurationCvMae')} for speed in ('blitz','rapid')}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'bothTrainingProceduresReproduced':True,'coefficientArtifactsWritten':False}))


if __name__=='__main__':main()
