"""Finite transition-system cross-check; not an EVM equivalence proof."""
from dataclasses import dataclass, asdict
from collections import deque
from itertools import combinations


@dataclass(frozen=True)
class State:
    nonce: int
    delegated: bool
    spent: bool = False
    debit: int = 0


def successors(s, inventory):
    # Each signature is immutable and reusable for submission; nonce guards use.
    for n in inventory:
        nxt = State(s.nonce+1, True, s.spent, s.debit) if n == s.nonce else s
        yield f'authorization({n})', nxt
    if s.delegated and not s.spent:
        yield 'session_call', State(s.nonce, True, True, s.debit+1)
    else:
        yield 'session_call', s


def explore(initial, inventory):
    queue = deque([(initial, [])])
    seen = {initial}
    witness = None
    edges = 0
    while queue:
        s, path = queue.popleft()
        if s.debit and witness is None:
            witness = path
        for label, nxt in successors(s, inventory):
            edges += 1
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [label]))
    return {'states': len(seen), 'edges': edges, 'counterexample': witness}


def certificate(state, inventory, complete_inventory=True, signer_frozen=True):
    """Sufficient only; supplied trust assumptions are not established by code."""
    return (complete_inventory and signer_frozen and not state.delegated
            and all(n < state.nonce for n in inventory))


def run_model():
    bad = explore(State(2, False), (0, 2))
    good = explore(State(3, False), (0, 2))
    assert bad['counterexample'] == ['authorization(2)', 'session_call']
    assert good['counterexample'] is None
    checked = states = edges = 0
    for k in range(7):
        for inv in combinations(range(6), k):
            for nonce in range(7):
                for delegated in (False, True):
                    s = State(nonce, delegated)
                    if certificate(s, inv):
                        r = explore(s, inv)
                        assert r['counterexample'] is None
                        checked += 1
                        states += r['states']
                        edges += r['edges']
    return {'counterexample': bad, 'repair': good,
            'certificate_instances_checked': checked,
            'reachable_states_for_certified_instances': states,
            'transition_checks_for_certified_instances': edges,
            'domain': 'all subsets of authorization nonces 0..5; boundary nonce 0..6; code empty/delegated',
            'scope': 'all finite traces in this finite abstraction, not arbitrary EVM contracts'}
