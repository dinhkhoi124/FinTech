# Banking77 Data Audit — W1-001

- Protocol: `banking77_w1_v1`
- Authoritative upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
- Official `test.csv` is frozen and excluded from tuning.

## Source checksums

- `categories.json`: `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63`
- `train.csv`: `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`
- `test.csv`: `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`

## Actual sample and label counts

- Official train: 10003
- Official test: 3080
- Total: 13083
- Intents: 77
- Official-train class range: 35–187
- Official-test class range: 40–40
- Locked-train class range: 31–168
- Validation class range: 4–19

## Integrity findings

- Empty text rows: 0
- Empty label rows: 0
- Invalid-label rows: 0
- Exact-query duplicate groups: 0
- Exact query-label duplicate groups: 0
- Conflicting-label query groups: 0
- Official train/test exact overlap: 0
- Official train/test case+whitespace-normalized overlap: 7 (7 label-consistent, 0 label-conflicting)
- Decision: preserve the authoritative official boundary and flag the 7 normalized overlaps as an evaluation limitation; do not remove or tune on test data.

### Normalized official train/test overlap cases

| Normalized query | Train label/text | Test label/text |
|---|---|---|
| at which atms can i use this card? | atm_support:  At which ATMs can I use this card? | atm_support: At which ATMs can I use this card? |
| how do i unblock my pin? | pin_blocked:  How do I unblock my PIN? | pin_blocked: How do I unblock my PIN? |
| i don't live in the uk. can i still get a card? | country_support: I don't live in the UK. Can I still get a card? | country_support: I don't live in the UK.  Can I still get a card? |
| there are a few transaction that i don't recognize, i think someone managed to get my card details and use it. | compromised_card: There are a few transaction that I don't recognize, I think someone managed to get my card details and use it.  | compromised_card: There are a few transaction that I don't recognize, I think someone managed to get my card details and use it. |
| what businesses accept this card? | card_acceptance: What businesses accept this card? | card_acceptance:   What businesses accept this card? |
| where can i use my card? | card_acceptance:  Where can I use my card? | card_acceptance: Where can I use my card? |
| which cash machines will allow me to change my pin? | change_pin:  Which cash machines will allow me to change my PIN? | change_pin: Which cash machines will allow me to change my PIN? |

## Unusually short queries

- Up to 1 token: 0
- Up to 2 tokens: 9
- Up to 3 tokens: 49

| Tokens | Label | Text |
|---:|---|---|
| 2 | `country_support` | Supported countries |
| 2 | `pending_transfer` | Pending transfer? |
| 2 | `cancel_transfer` | Cancel Transaction |
| 2 | `passcode_forgotten` | Lost password |
| 2 | `passcode_forgotten` | passcode retrieval |
| 2 | `exchange_via_app` | Change currency |
| 2 | `declined_transfer` | Transfer declined. |
| 2 | `pending_card_payment` | pending transaction? |
| 2 | `transfer_not_received_by_recipient` | transaction failed? |
| 3 | `declined_card_payment` | Card payment declined? |

## Locked protocol

- Strategy: `official_test_plus_hash_stratified_validation`
- Seed: `20260723`
- Train: 8998
- Validation: 1005
- Locked test: 3080
- Combined membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`

Detailed class distributions, short-query samples, membership IDs, and all counts are in the JSON artifacts.
