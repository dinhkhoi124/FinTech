# Configs

Version-controlled experiment and service configuration belongs here. Keep seeds,
data/split identifiers, model identifiers, and evaluation settings explicit. Do
not store credentials in config files.

Week 1 uses `data/banking77_w1_locked.json` as the immutable data contract.
`models/banking77_lexical_w1.json` contains the controlled W1-002 validation-only
comparison and the frozen lexical selection. The official test set is not a
model-selection input and remains reserved for W1-004.

`models/banking77_semantic_w1.json` pins the single W1-003 frozen encoder,
revision, normalization, downstream classifier, local cache contract, and
validation evidence paths. It permits no second encoder/configuration.

`evaluation/banking77_w1_final.json` is the W1-004 preregistration created before
official-test access. It pins both candidate hashes, identical 10,003-row final-fit
scope, metric/analysis definitions, decision rule, allowed reruns, prohibited
post-test changes, and final evidence paths.

Week 2 W2-001 uses `kb/kb_v1.json` as the controlled synthetic-KB contract. It
pins the ten canonical intents, fictional organization, fixed eligibility date,
schema, canonical JSONL source, generation guideline, document plan, hard-negative
matrix, validation thresholds, and evidence paths. It contains no retrieval
configuration, gold evidence mapping, embedding model, or index.
