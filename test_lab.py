import unittest
from eth_account import Account
from lab import Lab, PAYMENT, ZERO, primary_scenario
from model import State, certificate, run_model


class ContainmentTests(unittest.TestCase):
    def test_single_clear_future_authorization_counterexample(self):
        r = primary_scenario(False)
        self.assertEqual(r['post_boundary_debit_wei'], PAYMENT)
        self.assertFalse(r['property_holds_in_executed_trace'])
        self.assertFalse(any(x['after_stop'] and x['kind']=='ordinary' for x in r['signing_log']))

    def test_existing_nonce_horizon_recovery_same_starting_inventory(self):
        r = primary_scenario(True)
        self.assertEqual(r['post_boundary_debit_wei'], 0)
        self.assertTrue(r['property_holds_in_executed_trace'])
        self.assertEqual(r['events'][-1]['code'], '0x')

    def test_offchain_shutdown_alone_does_not_revoke_session(self):
        lab = Lab()
        lab.setup()
        before = lab.tester.get_balance(lab.authority)
        self.assertEqual(lab.call()['status'], 1)
        self.assertEqual(before-lab.tester.get_balance(lab.authority), PAYMENT)

    def test_one_clear_suffices_for_current_nonce_only_inventory(self):
        lab = Lab()
        initial, outstanding = lab.setup(future_nonce=1)
        lab.recover(1)
        before = lab.tester.get_balance(lab.authority)
        lab.relay([initial, outstanding], 'try_current_and_old')
        self.assertEqual(lab.tester.get_code(lab.authority), '0x')
        self.assertEqual(lab.tester.get_balance(lab.authority), before)

    def test_allowlist_raw_signing_and_freeze_enforced(self):
        lab = Lab()
        with self.assertRaises(PermissionError):
            lab.policy.authorize(lab, 0, target=lab.reverter)
        with self.assertRaises(PermissionError):
            lab.policy.raw_sign(b'any_payload')
        lab.policy.stopped = True
        with self.assertRaises(PermissionError):
            lab.policy.authorize(lab, 0)

    def test_allowlist_hash_pinning(self):
        lab = Lab()
        lab.policy.allowed_hash = bytes(32)
        with self.assertRaises(PermissionError):
            lab.policy.authorize(lab, 0)

    def test_delegate_rejects_other_caller_and_repeat_payment(self):
        lab = Lab()
        lab.setup()
        before = lab.tester.get_balance(lab.authority)
        self.assertEqual(lab.call(sender=0)['status'], 0)
        self.assertEqual(lab.tester.get_balance(lab.authority), before)
        self.assertEqual(lab.call()['status'], 1)
        self.assertEqual(lab.call()['status'], 0)
        self.assertEqual(before-lab.tester.get_balance(lab.authority), PAYMENT)

    def test_execution_revert_does_not_undo_authorization(self):
        lab = Lab()
        auth = lab.policy.authorize(lab, 0)
        receipt = lab.relay([auth], 'install_with_reverted_execution', to=lab.reverter)
        self.assertEqual(receipt['status'], 0)
        self.assertEqual(lab.tester.get_nonce(lab.authority), 1)
        self.assertTrue(lab.tester.get_code(lab.authority).startswith('0xef0100'))
        before = lab.tester.get_balance(lab.authority)
        lab.call()
        self.assertEqual(before-lab.tester.get_balance(lab.authority), PAYMENT)

    def test_execution_revert_does_not_undo_revocation(self):
        lab = Lab()
        lab.setup()
        clear = lab.policy.authorize(lab, 1, ZERO, recovery=True)
        receipt = lab.relay([clear], 'clear_with_reverted_execution', to=lab.reverter)
        self.assertEqual(receipt['status'], 0)
        self.assertEqual(lab.tester.get_code(lab.authority), '0x')
        self.assertEqual(lab.tester.get_nonce(lab.authority), 2)

    def test_wrong_chain_authorization_skipped_despite_success_receipt(self):
        lab = Lab()
        auth = Account.sign_authorization(
            {'chainId': lab.chain_id+1, 'address': lab.delegate, 'nonce': 0},
            lab.keys[1].to_bytes())
        receipt = lab.relay([auth], 'wrong_chain')
        self.assertEqual(receipt['status'], 1)
        self.assertEqual(lab.tester.get_code(lab.authority), '0x')
        self.assertEqual(lab.tester.get_nonce(lab.authority), 0)

    def test_wrong_nonce_clear_success_receipt_is_not_revocation(self):
        lab = Lab()
        lab.setup()
        clear = lab.policy.authorize(lab, 0, ZERO, recovery=True)
        receipt = lab.relay([clear], 'stale_clear', to=lab.neutral)
        self.assertEqual(receipt['status'], 1)
        self.assertTrue(lab.tester.get_code(lab.authority).startswith('0xef0100'))

    def test_model_and_refusal_when_assumptions_missing(self):
        r = run_model()
        self.assertIsNotNone(r['counterexample']['counterexample'])
        self.assertIsNone(r['repair']['counterexample'])
        self.assertFalse(certificate(State(3, False), (0, 2), complete_inventory=False))
        self.assertFalse(certificate(State(3, False), (0, 2), signer_frozen=False))
        self.assertFalse(certificate(State(2, False), (0, 2)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
