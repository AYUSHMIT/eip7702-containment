# Source and novelty record

Sources accessed 2026-11-05. No complete source articles are redistributed.
The experiment is grounded in protocol behavior, not the accuracy of incident
loss estimates or unverified claims about Binance's internal systems.

1. **EIP-7702, final specification**, Behavior and Security Considerations.
   https://eips.ethereum.org/EIPS/eip-7702
   Protocol basis: authorization nonce equality, increment after application,
   zero-target code clearing, and authorization effects persisting despite a
   later execution revert. The test uses these semantics without alteration.

2. **Ethereum Foundation, Pectra EIP-7702 guidance**.
   https://ethereum.org/roadmap/pectra/7702
   Confirms delegation removal and the owner's continuing key authority.
   Delegation is not a way to remove the root key's power to sign.

3. **Fellowship of Ethereum Magicians, ja7ad, post #418, 2026-10-30**.
   https://ethereum-magicians.org/t/eip-7702-set-eoa-account-code/19923/418
   Direct novelty blocker. The author describes withheld higher-nonce
   authorizations restoring delegation after recovery has advanced the nonce,
   even after access to the signing service stops. The same post proposes
   consuming the compromised nonce range before returning the wallet to use.
   This is a dated public technical discussion, not a peer-reviewed proof or
   an authoritative incident reconstruction. It suffices to defeat a claim
   that this failure mechanism or recovery principle is newly identified here.

4. **Fireblocks, Deconstructing the Binance Exploit, 2026-10-30**.
   https://www.fireblocks.com/blog/binance-hack-eip-7702
   Documents authorization-level delegation allowlisting, raw-signing
   restrictions, and independent checks. Those are relevant strong preventive
   control classes. This artifact implements a transparent toy policy gate,
   not Fireblocks code. No Fireblocks audit, bypass, or product vulnerability
   is claimed. Allowlisting an address alone does not specify session lifecycle.

5. **Alchemy, How EIP-7702 works**.
   https://www.alchemy.com/docs/wallets/transactions/using-eip-7702
   Documents delegation removal using the zero target and distinguishes
   sponsored and self-originated transaction construction. We use a separate
   sponsor, so the authority's authorization nonce is its current nonce.
   This is baseline provenance, not a claim that Alchemy promises universal
   post-removal containment or permits arbitrary future-nonce issuance.

6. **DeFi Security Alliance, EIP7702 Revocation**, published 2026-09-20,
   updated 2026-10-03.
   https://defisec.info/blog/eip7702-revocation
   Reports an earlier constructed revocation model and distinguishes current
   code, receipt interpretation, retained permissions and remaining key power.
   Thus a generic receipt-versus-state checker also has clear antecedents.

7. **Py-EVM release notes**.
   https://py-evm.readthedocs.io/en/latest/release_notes.html
   Records EIP-7702 support in the Prague implementation. Py-EVM is archived;
   this run intentionally pins the last supported Prague implementation,
   rather than claiming to test all current/future Ethereum forks.

8. **eth-account 0.13.7 reference**.
   https://eth-account.readthedocs.io/en/v0.13.7/eth_account.html
   Signing library reference. Actual dependency versions are in the lockfile.

## Decision

The experiment separates three propositions:

- A single code clear proves that current delegation is gone at that state.
- It does not, by itself, prove that all pre-issued capabilities are unusable.
- With a frozen signer, complete finite inventory and appropriate nonce
  invalidation, existing mechanisms satisfy the chosen native-outflow property.

The primary counterexample and repair need no novel cryptography or protocol
extension. A small checking script is useful for regression evidence, but this
work establishes no distinct verification method or publishable contribution.
**Record the result and stop this specific lead**, as requested. This is not
an exhaustive claim that all custody-containment research is solved.
