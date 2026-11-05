# Property P: no post-containment debit from old capabilities

## Actors and scope

- A: the authority EOA holding native currency on one fixed Prague chain.
- D: an immutable, allowlisted one-shot payment delegate.
- S: the session operator; its credential may remain usable by the attacker.
- H: the owner signing system. It is honest for this experiment, checks D's
  address and bytecode hash, and disables raw-signing bypasses.
- R: an uncompromised recovery path to **A's same signing key**. EIP-7702 does
  not grant an unrelated key the power to revoke A's delegation. After ordinary
  signing is frozen, R may issue only zero-target recovery authorizations.
- Sigma: the complete set of ordinary A-signed EIP-7702 authorizations issued
  before the stop. In the primary pair its nonces are exactly {0, 2}.

The operator can create arbitrary transactions from its own accounts, submit
members of Sigma repeatedly, and call A. It cannot forge signatures by A or
obtain new ordinary signatures after the stop. The test driver knows all local
genesis keys to create the fixture; adversarial actions in the trace use only
the session key and the already signed authorization objects.

There are no other pending A-originated transactions, signed permits, token
allowances, external asset handlers, chain-zero authorizations or other chains.
The property concerns native outflow from A only. Admission of more capability
types would require revisiting the assumptions and evaluator, not silently
extending this result.

## Formal statement

Let s_c be the state at the containment boundary, after the recovery transaction
has been applied. Let T(Sigma, s_c) be all finite traces produced by the above
adversarial actions with no subsequent owner-authorized reopening. Define
Debit_A(tau) as the sum of native value transferred out of A during tau.

    P(Sigma, s_c) := for every tau in T(Sigma, s_c), Debit_A(tau) = 0.

Recovery costs are incurred before this boundary, and A does not sponsor
transactions in the experiment. Incoming transfers are not counted as negative
debits. The executed traces contain no incoming transfers, so authority balance
loss plus the corresponding recipient gain is an adequate oracle for them.

The boundary is assumed irreversible. eth-tester mines local blocks but does
not model Ethereum consensus finality, reorgs, private mempools or censorship.
The claim does not cover losses between stop request and completed recovery.

## Applicable baseline and counterexample

B1 signs a zero-target authorization for A's current nonce, includes it in a
sponsored type-4 transaction, checks that A's code is empty, and declares P.
This uses the existing in-protocol revocation mechanism. The overclaim lies in
declaring P from that state alone.

Both ordinary signatures in the primary case are issued before stop and both
pass the delegate allowlist. Future-nonce issuance is an explicit permitted
operating rule, not a behavior attributed to a particular wallet product.
Authorization 0 installs D and advances A to nonce 1, without executing D.
The clear at nonce 1 leaves empty code and nonce 2. A pre-stop signature at
nonce 2 is then valid: it reinstalls D and permits S's one previously authorized
payment. Consequently Debit_A(tau)=1,000,000 test wei and P is false for B1.

This distinguishes an off-chain policy revocation from an on-chain invalidation.
The call was authorized before stop; after a valid containment declaration the
selected policy forbids it. There is no unauthorized arbitrary-code delegate
and no post-stop owner-signature request in this witness.

## Existing recovery under the same assumptions

Let H_max be the largest nonce in the complete inventory Sigma. Apply standard
zero-target authorizations at each remaining nonce through H_max (also clear
the current nonce if it already exceeds H_max). Verify actual account state.
In the primary pair, clears at 1 and 2 execute in one sponsored transaction;
the resulting account has empty code and nonce 3.

The following is a sufficient condition, not claimed necessary:

    C := ordinary signing frozen
         AND inventory Sigma complete
         AND code(A, s_c) is empty
         AND every alpha in Sigma has alpha.nonce < nonce(A, s_c).

Conditional argument that C implies P within the declared action model:

1. No inventory authorization can pass the exact nonce check at s_c.
2. Re-submitting invalid authorizations cannot install delegate code. Direct
   calls to an empty-code A cannot initiate a native transfer from A.
3. No action available to the attacker introduces a fresh A signature, an
   A-originated spending transaction, or an alternative outflow permission.
4. These facts are preserved after each permitted action. Induction on finite
   trace length yields zero outflow throughout the suffix.

The EVM execution tests validate concrete instances of the protocol rules;
the finite model checks the simplified transition system. The prose argument
is not a machine-checked EVM proof, and the toy `certificate` function does not
establish the truth of its externally supplied completeness/freeze assumptions.

## Why the conclusion is bounded

An incomplete or untrusted signing ledger provides no defensible H_max. The
checker refuses its sufficient condition when completeness or freeze is absent.
A signer holding the raw key can always issue new valid signatures; changing
the delegate alone cannot eliminate that authority.

Advancing through a very large nonce range may be costly or impractical. We
claim neither bounded recovery cost nor guaranteed inclusion. Concurrent
submissions can change the current nonce; the terminal state, not a planned
transaction or receipt status, must satisfy C. A stale clear may be skipped.
The local fixture deliberately isolates the post-completion safety property.

None of these limits supplies novelty by itself. The observed failure and
nonce-range recovery principle already appear in prior public discussion.
