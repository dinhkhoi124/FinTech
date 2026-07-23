# Configs

Version-controlled experiment and service configuration belongs here. Keep seeds,
data/split identifiers, model identifiers, and evaluation settings explicit. Do
not store credentials in config files.

Week 1 uses `data/banking77_w1_locked.json` as the immutable data contract.
`models/banking77_lexical_w1.json` contains the controlled W1-002 validation-only
comparison and the frozen lexical selection. The official test set is not a
model-selection input and remains reserved for W1-004.
