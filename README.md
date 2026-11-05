# EIP-7702 containment gate

Completed 2026-11-05. **Decision: STOP this narrow novelty lead.**

We reproduced a real protocol-level failure of treating a single delegation
clear as permanent containment. Existing nonce invalidation and delegation
revocation satisfy the selected property under the same finite-capability
assumptions. Prior public discussion already describes both the failure and
the recovery principle. No new cryptographic construction, protocol change,
or distinct verification method is justified by this result.

This is a small offline security regression fixture. It is not a reconstruction
of the Binance incident, an audit of Fireblocks/Alchemy, a production wallet,
or evidence of a new exploit in a named product.

## One property

After a declared irreversible containment boundary, an attacker holding only
the explicitly enumerated pre-stop EIP-7702 authorizations and the old session
credential cannot cause any further native-currency debit from the authority.
No fresh owner signatures, owner-originated pending transactions, other asset
permissions, or chain reorganizations are admitted. See [PROPERTY.md](PROPERTY.md)
for quantifiers, trusted components, and the proof boundary.

## Primary comparison: identical starting capabilities

The signed authorization inventory is `{nonce 0, nonce 2}`, both targeting the
same allowlisted immutable delegate. The delegate permits one payment of
1,000,000 test wei from a fixed session caller to a fixed recipient. It rejects
other callers and repeated payments. Future-nonce pre-signing is explicitly
permitted in this model; the key itself is not compromised.

| Step | Single-clear baseline | Existing nonce-aware recovery |
| --- | --- | --- |
| Install authorization 0 without making a payment | Nonce 1, delegate installed | Same |
| Stop ordinary signing and the application service | No new ordinary owner signatures | Same |
| Apply zero-target revocation(s) | Clear at nonce 1 | Clear at nonces 1 and 2 |
| Declare containment | Nonce 2, empty code | Nonce 3, empty code |
| Submit pre-stop authorization 2 and call authority | Delegate restored; payment succeeds | Authorization skipped; no code executes |
| Post-boundary native debit | **1,000,000 test wei** | **0** |

The owner pays no transaction gas in either case; other local test accounts
sponsor every transaction. Recipient gains match authority debits. No deposits
occur during the measured suffix, so balance changes cannot mask an outflow.

The baseline is the standard zero-target clear, combined with an excessively
strong interpretation of its outcome. It successfully clears current code.
The experiment does **not** claim that EIP-7702 promises to cancel every
future-nonce signature, or that any named vendor makes that promise.

## Evidence and what passed

- 12 tests on an actual in-memory Prague EVM, with signed type-4 transactions.
- Baseline counterexample and same-assumption recovery trace saved as JSON.
- Additional checks: off-chain stop alone; current-nonce-only inventory;
  wrong chain; stale revocation nonce; execution revert; caller and replay
  restrictions; signer freeze; delegate allowlist and code-hash pinning.
- A finite abstraction exhaustively checks 127 states satisfying the sufficient
  containment condition, across all inventories drawn from nonces 0..5 and
  boundary nonces 0..6. These yield 448 transition checks. This is a small
  sanity check, not an equivalence proof for EVM bytecode or a scale result.
- Saved signatures, transaction hashes, transfer accounting and equality of
  the primary starting inventories are checked independently of the runner's
  reported pass flag.

## Reproduce

Use Python 3.12 on Linux; the recorded run used Python 3.12.14.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest -v test_lab
.venv/bin/python run.py --output replay-results
.venv/bin/python check_results.py replay-results
```

Dependency installation requires package access. The experiment itself needs
no network, RPC endpoint, browser, credentials, GPU or real funds. All keys
and addresses are eth-tester's disposable genesis fixtures. The EVM backend is
explicitly pinned to Prague, not represented as validation of all later forks.
Block hashes/timestamps may change on replay; the signed transactions and
relevant nonce, code and balance outcomes are the reproducibility target.

`requirements-lock.txt` records exact installed versions. `SHA256SUMS.txt`
covers the delivered source and saved evidence. `verify_archive.py` checks it
using only the Python standard library. Dependency files are not bundled.

## How to read the archive

| File | Purpose |
| --- | --- |
| PROPERTY.md | Formal property, assumptions, sufficient condition and argument |
| SOURCES.md | Primary sources and novelty decision |
| lab.py | Local EVM fixture, signer controls, baseline and existing recovery |
| model.py | Small exhaustive abstract transition check |
| test_lab.py | 12 regression and negative-control tests |
| run.py | Generate both primary traces and model results |
| check_results.py | Saved-evidence consistency and cryptographic checks |
| results/ | Signed transactions, signatures, state observations and test logs |
| DECISION.json | Machine-readable stop decision and its scope |

## Stop decision and limits

Ordinary allowlisting alone does not revoke an allowed session. Under the
primary assumptions, allowlisting plus a signer freeze, complete authorization
inventory, and existing nonce-aware clearing suffice. If only current-nonce
authorizations exist, one correctly applied clear suffices in the tested variant.

We therefore stop at a reproducible validation example. The broad claim that
an arbitrary real custody system is contained remains unproved. Missing signer
history, fresh signatures after compromise, token approvals, permit signatures,
other chains, and finality or inclusion failures are outside this result. In
particular, reading empty code cannot reveal withheld off-chain signatures.
No unconditional recovery certificate or recovery-latency guarantee is claimed.

No ICC evidence, Unity job or Slack channel was changed.
