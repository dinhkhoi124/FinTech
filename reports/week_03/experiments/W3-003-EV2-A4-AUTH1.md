# W3-003-EV2-A4-AUTH1 — local real A4 authorization receipt

Status: `A4_AUTHORIZATION_RECEIPT_READY_FOR_SENIOR_EXECUTION_REVIEW`.

The exact CPython 3.11.9 offline JIT re-attestation reproduced ATT1 fingerprint
`f49e29f3ad3338a191f50e42e28fd2335a36f670541c9eb7337f0bcdcb478a7d` and
all six required JIT evidence hashes. Fresh remote and all protected state
remained unchanged.

The local A4 V3 receipt is bound to the frozen A3 manifest, R0 decision, source
tree, runtime inputs, published ATT1 identities, and unique nonce
`W3-003-EV2-A4-AUTH1-20260825-0001`. `validate_a4()` passed. In-memory
mutations for authorization, EV2 flag, R1, retrieval-decision SHA, A3 SHA, E1
SHA, and an empty nonce were all rejected.

At AUTH1 task completion, the receipt, validation audit, JIT directory, and
detached bundle were untracked and intentionally unpublished. PUB1 later
publishes the AUTH1 receipt and validation audit alongside Senior-accepted
canonical E1 evidence; the JIT directory and detached bundle remain excluded.
AUTH1 itself did not execute E1 or EV2, invoke production runner/retrieval,
start row 1, create consumption/raw output, stage, commit, or push.
