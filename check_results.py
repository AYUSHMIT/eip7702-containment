"""Check saved records, authorization signatures, and transaction hashes.

This is an integrity/consistency check. It does not establish that a real signer
has disclosed its complete signing inventory. Re-execute run.py for an EVM check.
"""
import json
import sys
from pathlib import Path
import rlp
from eth_keys import keys
from eth_utils import keccak, to_checksum_address


def check(directory):
    results = []
    for filename, nonce, expected_debit in [
        ('counterexample.json', 2, 1_000_000),
        ('existing_recovery.json', 3, 0)]:
        d = json.loads((directory/filename).read_text())
        for row in d['signing_log']:
            a = row['authorization']
            target = bytes.fromhex(a['address'][2:])
            digest = keccak(b'\x05' + rlp.encode([a['chain_id'], target, a['nonce']]))
            signer = keys.Signature(vrs=(a['y_parity'],a['r'],a['s'])).recover_public_key_from_msg_hash(digest)
            assert signer.to_checksum_address() == d['authority']
            assert a['chain_id'] == d['chain_id']
            if row['kind'] == 'ordinary':
                assert not row['after_stop']
                assert to_checksum_address(a['address']) == d['delegate']
        txs = {t['tx_hash']: t for t in d['transactions']}
        for tx in txs.values():
            assert '0x'+keccak(bytes.fromhex(tx['raw_transaction'][2:])).hex() == tx['tx_hash']
            assert tx['sender'] != d['authority'], 'authority must not pay transaction gas'
        for e in d['events']:
            if 'tx_hash' in e:
                t = txs[e['tx_hash']]
                assert (t['receipt_status'],t['block']) == (e['receipt_status'],e['block'])
        boundary = next(e for e in d['events'] if e['label']=='recovery_boundary')
        final = d['events'][-1]
        assert boundary['code'] == '0x' and boundary['nonce'] == nonce
        assert boundary['authority_balance_wei']-final['authority_balance_wei'] == expected_debit
        assert final['beneficiary_balance_wei']-boundary['beneficiary_balance_wei'] == expected_debit
        assert d['post_boundary_debit_wei'] == expected_debit
        assert d['property_holds_in_executed_trace'] == (expected_debit == 0)
        results.append(d)
    # Primary baseline and repair must start with exactly the same capabilities.
    ordinary = [[r['authorization'] for r in d['signing_log'] if r['kind']=='ordinary'] for d in results]
    assert ordinary[0] == ordinary[1]
    assert results[0]['delegate_runtime_hex'] == results[1]['delegate_runtime_hex']
    print('PASS: signatures, transaction hashes, same starting capabilities, boundary states and transfer accounting')


if __name__ == '__main__':
    check(Path(sys.argv[1] if len(sys.argv)>1 else 'results'))
