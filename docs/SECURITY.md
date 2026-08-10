# Security boundaries

HumAIn is designed around a hostile or merely unreliable transport. That does not make the first implementation secure by magic.

## Threats addressed by the substrate

- ambiguous pointer/action scope;
- expired capabilities;
- revoked capabilities;
- audience mismatch;
- broken parent/hash linkage;
- replay of a previously seen nonce within a resolver instance;
- confusing demo signatures with verified signatures;
- overwriting closed receipts.

## Threats not addressed yet

- private-key storage or hardware-backed signing;
- origin control or DNS compromise;
- malicious browser extensions;
- compromised agent runtimes;
- side channels, screenshots, clipboard leakage, or OS telemetry;
- transport availability or relay censorship;
- truthfulness of publisher claims or observations;
- correlation of public pointers into a person's identity;
- regulated custody, payments, token issuance, or financial claims.

## Security posture

The resolver must fail closed for capability checks. A missing signature, expired grant, revoked grant, mismatched audience, or pointer outside scope is not silently upgraded to access.

The protocol deliberately separates authentication from truth. A valid signature can establish control of a key. It does not prove that the signed observation is accurate.

“Mutual capability authentication” is not automatically two-factor authentication. Two proofs produced on one device may not be independent factors.
