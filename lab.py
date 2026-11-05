"""Offline Prague EVM experiment; no RPC, real keys, or external addresses.

All actors are eth-tester genesis accounts. The one-shot delegate is a small
allowlisted test fixture, not a production wallet or a vendor implementation.
"""
from dataclasses import dataclass
from eth_account import Account
from eth_tester import EthereumTester, PyEVMBackend
from eth.vm.forks.prague import PragueVM
from eth_utils import keccak

ZERO = '0x' + '00' * 20
PAYMENT = 1_000_000


def push(value, width=None):
    if isinstance(value, str):
        raw = bytes.fromhex(value.removeprefix('0x'))
    else:
        raw = value.to_bytes(width or max(1, (value.bit_length()+7)//8), 'big')
    return bytes([0x5f + len(raw)]) + raw


def one_shot_runtime(session, beneficiary):
    """Caller-restricted, fixed-recipient, fixed-value, at-most-once payment.

    Equivalent behavior: require(msg.sender==SESSION && storage[0]==0);
    storage[0]=1; require(BENEFICIARY.call{value:PAYMENT}(empty));
    Failure reverts including the slot write. Runtime has no upgrade path.
    """
    b = bytearray()
    jumps = []
    def fail_if_true():
        b.extend(b'\x61\x00\x00\x57')  # PUSH2 <fail>; JUMPI
        jumps.append(len(b)-3)
    b.extend(b'\x33' + push(session) + b'\x14\x15')  # caller != session
    fail_if_true()
    b.extend(push(0) + b'\x54')  # spent != 0
    fail_if_true()
    b.extend(push(1) + push(0) + b'\x55')  # spent = 1
    b.extend(push(0)*4 + push(PAYMENT) + push(beneficiary) + b'\x5a\xf1\x15')
    fail_if_true()  # CALL failed
    b.append(0x00)
    label = len(b)
    b.extend(b'\x5b' + push(0)*2 + b'\xfd')
    for p in jumps:
        b[p:p+2] = label.to_bytes(2, 'big')
    return bytes(b)


def creation(runtime):
    # 15-byte init prefix: CODECOPY runtime to memory; RETURN runtime.
    return (push(len(runtime), 2) + push(15, 2) + push(0) + b'\x39'
            + push(len(runtime), 2) + push(0) + b'\xf3' + runtime)


@dataclass
class SignerPolicy:
    """Transparent test implementation of controls, not Fireblocks software.

    Allowlisting is applied to the signed delegate itself, with immutable
    bytecode-hash pinning. Raw signing has no bypass. Future nonce signing is
    explicitly allowed in the primary experiment; variants constrain it.
    """
    allowed_address: str
    allowed_hash: bytes
    stopped: bool = False

    def authorize(self, lab, nonce, target=None, recovery=False):
        target = target or lab.delegate
        if recovery:
            if target != ZERO:
                raise PermissionError('Recovery can only clear code')
        else:
            if self.stopped:
                raise PermissionError('Signing stopped')
            if target != self.allowed_address:
                raise PermissionError('Delegate not allowlisted')
            code = bytes.fromhex(lab.tester.get_code(target)[2:])
            if keccak(code) != self.allowed_hash:
                raise PermissionError('Allowlisted bytecode hash changed')
        auth = Account.sign_authorization(
            {'chainId': lab.chain_id, 'address': target, 'nonce': nonce},
            lab.keys[1].to_bytes())
        lab.signed.append({'nonce': nonce, 'address': target,
                           'kind': 'recovery' if recovery else 'ordinary',
                           'after_stop': self.stopped,
                           'authorization': auth.model_dump()})
        return auth

    def raw_sign(self, payload):
        raise PermissionError('Raw signing disabled')


class Lab:
    def __init__(self):
        self.backend = PyEVMBackend(vm_configuration=((0, PragueVM),))
        self.tester = EthereumTester(backend=self.backend)
        self.accounts = self.tester.get_accounts()
        self.keys = self.backend.account_keys
        self.sponsor, self.authority, self.session, self.beneficiary = self.accounts[:4]
        self.neutral = self.accounts[4]
        self.chain_id = self.backend.chain.chain_id
        self.events = []
        self.signed = []
        self.transactions = []
        self.runtime = one_shot_runtime(self.session, self.beneficiary)
        self.delegate = self.deploy(self.runtime)
        self.reverter = self.deploy(bytes.fromhex('60006000fd'))
        self.policy = SignerPolicy(self.delegate, keccak(self.runtime))
        self.capture('initial')

    def send(self, sender_index, to=None, data=b'', authorizations=None):
        sender = self.accounts[sender_index]
        tx = {'type': 4 if authorizations is not None else 2,
              'chainId': self.chain_id,
              'nonce': self.tester.get_nonce(sender),
              'gas': 500_000,
              'maxFeePerGas': 10**10, 'maxPriorityFeePerGas': 10**9,
              'value': 0, 'data': data}
        if to is not None:
            tx['to'] = to
        if authorizations is not None:
            tx['authorizationList'] = authorizations
        signed = Account.sign_transaction(tx, self.keys[sender_index].to_bytes())
        h = self.tester.send_raw_transaction('0x' + signed.raw_transaction.hex())
        receipt = self.tester.get_transaction_receipt(h)
        self.transactions.append({'sender': sender, 'to': to,
                                  'raw_transaction': '0x' + signed.raw_transaction.hex(),
                                  'tx_hash': h, 'receipt_status': receipt['status'],
                                  'block': receipt['block_number']})
        return receipt

    def deploy(self, runtime):
        receipt = self.send(0, data=creation(runtime))
        assert receipt['status'] == 1, receipt
        address = receipt['contract_address']
        assert self.tester.get_code(address) == '0x' + runtime.hex()
        return address

    def capture(self, label, receipt=None):
        block = self.tester.get_block_by_number('latest')
        event = {'label': label, 'block': block['number'], 'block_hash': block['hash'],
                 'nonce': self.tester.get_nonce(self.authority),
                 'code': self.tester.get_code(self.authority),
                 'authority_balance_wei': self.tester.get_balance(self.authority),
                 'beneficiary_balance_wei': self.tester.get_balance(self.beneficiary),
                 'slot0': self.tester.get_storage_at(self.authority, '0x0')}
        if receipt is not None:
            event.update(receipt_status=receipt['status'], gas_used=receipt['gas_used'],
                         tx_hash=receipt['transaction_hash'])
        self.events.append(event)
        return event

    def relay(self, auths, label, to=None):
        receipt = self.send(2, to or self.authority, authorizations=auths)
        self.capture(label, receipt)
        return receipt

    def call(self, label='session_call', sender=2):
        receipt = self.send(sender, self.authority)
        self.capture(label, receipt)
        return receipt

    def setup(self, future_nonce=2):
        initial = self.policy.authorize(self, 0)
        future = self.policy.authorize(self, future_nonce)
        self.relay([initial], 'install_without_spending', to=self.neutral)
        assert self.tester.get_nonce(self.authority) == 1
        self.policy.stopped = True
        self.capture('offchain_stop')
        return initial, future

    def recover(self, horizon):
        start = self.tester.get_nonce(self.authority)
        # Always clear current code; additionally invalidate all recorded nonces.
        stop = max(start, horizon)
        auths = [self.policy.authorize(self, n, ZERO, recovery=True)
                 for n in range(start, stop + 1)]
        return self.relay(auths, 'recovery_boundary', to=self.neutral)

    def export(self):
        return {'chain_id': self.chain_id, 'fork': 'Prague',
                'authority': self.authority, 'session': self.session,
                'beneficiary': self.beneficiary, 'delegate': self.delegate,
                'delegate_runtime_hex': self.runtime.hex(),
                'delegate_keccak256': keccak(self.runtime).hex(),
                'payment_wei': PAYMENT, 'signing_log': self.signed,
                'events': self.events, 'transactions': self.transactions}


def primary_scenario(repair=False):
    lab = Lab()
    initial, future = lab.setup()
    lab.recover(2 if repair else 1)
    boundary = lab.events[-1]
    assert boundary['code'] == '0x'
    lab.relay([future], 'submit_pre_stop_nonce_2_and_call')
    lab.relay([initial, future], 'retry_both_old_authorizations')
    lab.call('direct_call_after_replay')
    last = lab.events[-1]
    loss = boundary['authority_balance_wei'] - last['authority_balance_wei']
    gain = last['beneficiary_balance_wei'] - boundary['beneficiary_balance_wei']
    assert loss == gain == (0 if repair else PAYMENT)
    result = lab.export()
    result.update(scenario='nonce_horizon_recovery' if repair else 'single_clear_counterexample',
                  containment_boundary_block=boundary['block'],
                  post_boundary_debit_wei=loss,
                  property_holds_in_executed_trace=(loss == 0))
    return result
