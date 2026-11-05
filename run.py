"""Generate replayable evidence using the local in-memory EVM only."""
import argparse
import importlib.metadata
import json
import platform
from pathlib import Path
from lab import primary_scenario
from model import run_model


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='results')
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    evidence = {
        'counterexample.json': primary_scenario(False),
        'existing_recovery.json': primary_scenario(True),
        'finite_model.json': run_model(),
        'environment.json': {'python': platform.python_version(),
                             'packages': {x: importlib.metadata.version(x) for x in
                                          ('eth-tester','py-evm','eth-account')},
                             'backend': 'in-memory Prague EVM, no RPC',
                             'finality': 'assumed irreversible boundary; no consensus simulation'}}
    for name, value in evidence.items():
        (out/name).write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps({'counterexample_debit_wei': evidence['counterexample.json']['post_boundary_debit_wei'],
                      'existing_recovery_debit_wei': evidence['existing_recovery.json']['post_boundary_debit_wei'],
                      'finite_model': evidence['finite_model.json']}, indent=2))


if __name__ == '__main__':
    main()
