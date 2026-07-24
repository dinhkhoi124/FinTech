# 5-Week AI Engineering Workflow

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 10.

---

# 10. 5-Week AI Engineering Workflow — Solo Scope

## Nguyên tắc phân bổ

Mỗi tuần chỉ có **một P0 outcome chính**. P1 chỉ được mở khi P0 đã có bằng chứng.

---

# Week 1 — Banking77 Benchmark & Error Analysis

## P0 Outcome

> Có benchmark intent classification reproducible trên full Banking77 và biết model sai ở đâu.

### P0 Tasks

1. Data audit đủ để phát hiện vấn đề lớn:
   - class distribution;
   - duplicate/near-duplicate hợp lý;
   - split/leakage check cơ bản.
2. Locked split.
3. Baseline 1: TF-IDF + Logistic Regression hoặc tương đương.
4. Baseline 2: một semantic/model-based approach.
5. Đánh giá:
   - Accuracy;
   - Macro-F1;
   - per-class F1;
   - confusion matrix.
6. Error analysis top confusion pairs.
7. Unit tests tối thiểu:
   - label mapping;
   - preprocessing/input contract.

### P1 nếu còn thời gian

- confidence calibration;
- OOS/OOD detection;
- model thứ ba;
- extensive data-quality mining.

### P0 Deliverables

- `intent_benchmark.csv/md`.
- Reproducible split/config.
- Confusion/error-analysis note.
- Tests tối thiểu.

### Exit Criteria

Không sang experiment model khác nếu chưa trả lời được:

```text
Baseline nào tốt hơn và vì sao?
Intent nào đang khó?
Lỗi là data, semantic overlap hay model capacity?
```

---

# Week 2 — Synthetic KB + Retrieval R0/R1

## P0 Outcome

> Có một KB versioned đủ tốt để benchmark retrieval và chứng minh intent-aware retrieval có/không có lợi.

### P0 Tasks

1. Chọn khoảng **8–12 intents** cho RAG subset.
2. Thiết kế schema.
3. Tạo target **30–40 documents** nhưng ưu tiên chất lượng. Nếu đến giữa Week 2 gold mapping chưa ổn, **scope-lock ở 24–30 documents chất lượng** thay vì sinh thêm:
   - FAQ;
   - Policy;
   - Runbook;
   - Escalation Guide;
   - `APPROVED / DRAFT / EXPIRED`;
   - version conflict;
   - hard negatives.
4. Validation:
   - schema;
   - status/version;
   - coverage.
5. Xây gold evidence mapping cho eval set.
6. Chunk/index một cấu hình hợp lý.
7. R0: approved-only retrieval.
8. R1: approved-only + intent-aware.
9. Đo Recall/Hit@K, MRR nếu phù hợp, leakage rate.
10. Error analysis một số failure tiêu biểu.

### P1 nếu còn thời gian

- hybrid BM25+dense;
- reranker;
- embedding A/B;
- chunk-size study;
- mở KB sang 15–20 intents.

### P0 Deliverables

- `kb_v1`.
- KB schema + generation guideline.
- Gold evidence mapping.
- R0 vs R1 benchmark.
- Validation tests.

### Exit Criteria

```text
Gold evidence mapping đáng tin?
DRAFT/EXPIRED leakage = 0?
R0 vs R1 có cùng điều kiện so sánh?
Biết intent signal giúp/hại ở case nào?
```

---

# Week 3 — Grounded RAG + Critical Safety Evaluation

## P0 Outcome

> Hệ thống trả lời có evidence hoặc dừng an toàn; safety được chứng minh trên critical set.

### P0 Tasks

1. Tích hợp:
   - classifier;
   - R1 hoặc retrieval variant tốt nhất từ Week 2;
   - approved filtering;
   - grounded generation.
2. Citation output.
3. Evidence gate đơn giản, có rule rõ.
4. Hai response mode bắt buộc:
   - `ANSWER`;
   - `ABSTAIN/ESCALATE`.

`ASK_CLARIFICATION` là P1, không bắt buộc P0.

5. Critical eval set khoảng 60–100 query chất lượng.
6. Đo:
   - citation correctness;
   - unsupported answer rate;
   - abstention correctness;
   - end-to-end safe resolution.
7. Hai ablation P0:
   - R0 vs R1;
   - always-answer vs evidence-gated.
8. Biến failure nghiêm trọng thành regression test.

### P1 nếu còn thời gian

- ask clarification;
- automated faithfulness judge;
- filter-vs-no-filter ablation;
- failure propagation E1–E5 đầy đủ;
- OOS suite lớn.

### P0 Deliverables

- End-to-end grounded pipeline.
- Critical eval set.
- Evaluation script.
- 2 core comparison tables.
- Safety/error analysis.
- Regression tests.

### Exit Criteria

```text
Không có evidence thì hệ thống làm gì?
Unsupported answer rate là bao nhiêu?
Intent-aware retrieval có cải thiện end-to-end hay chỉ retrieval metric?
```

---

# Week 4 — Minimal Service + One Incident

## P0 Outcome

> Prototype không còn chỉ ở notebook: chạy qua API, trace được version, và debug được một regression.

### P0 Engineering

- 1 endpoint `/query`.
- Input validation.
- Structured response.
- Structured logging tối thiểu:
  - timestamp/request_id;
  - predicted_intent;
  - retrieved_doc_ids;
  - response_type;
  - model_version;
  - kb/index_version;
  - total latency.
- Config tách code.
- Secret không hard-code.
- Unit tests cho safety invariants.
- Ít nhất 1 E2E regression test.

### P0 Incident

Inject một thay đổi KB gây regression, ví dụ:

> Version mới bị metadata sai hoặc document draft bị promote nhầm.

Thực hiện:

```text
reproduce
→ compare versions
→ isolate root cause
→ fix/rollback
→ rerun eval
→ add regression test
→ short postmortem
```

### P1 nếu còn thời gian

- health check;
- timeout/retry nâng cao;
- Docker;
- Streamlit/Gradio;
- integration-test suite lớn;
- stage-level latency tracing.

### P0 Deliverables

- Runnable API/service.
- Minimal logs/version tracking.
- Tests.
- Incident postmortem.
- Regression test.

### Exit Criteria

> Có thể chứng minh một thay đổi KB/model đã làm gì với metric và có thể rollback/fix bằng evidence.

---

# Week 5 — Final Evidence + One Deep Change Request

## P0 Outcome

> Chốt bằng chứng nghiên cứu/kỹ thuật và chứng minh tư duy system design trên **một** requirement mới.

### P0 Tasks

1. Freeze versions.
2. Chạy final evaluation một lần trên locked test/eval sets.
3. Tổng hợp:
   - classification benchmark;
   - R0 vs R1 retrieval;
   - evidence-gated vs always-answer;
   - safety/end-to-end results;
   - major failures/limitations.
4. Chọn **1 change request** để phân tích sâu:
   - Scale;
   - Daily Policy Update;
   - Vietnamese/Multilingual;
   - New Unseen Intent.
5. Technical report ngắn, evidence-driven.
6. Demo 4–5 case.

### P1 nếu còn thời gian

- Change request thứ hai.
- UI polish.
- Extended benchmark.
- Failure propagation full taxonomy.

### P2 — Không triển khai

Ba change request còn lại được giữ như backlog/system-design prompts, không xem là deliverable implementation.

## Final P0 Deliverables

1. Intent benchmark.
2. Synthetic KB + validation/gold mapping.
3. R0 vs R1 retrieval benchmark.
4. Grounded/safety evaluation.
5. Minimal service + logs/version.
6. Incident postmortem.
7. One deep change-request design note.
8. Concise technical report.
9. Demo.

## Exit Criteria

Project thành công khi có **ít artifact hơn nhưng mỗi claim chính đều có evidence**:

```text
Claim
→ experiment/test
→ metric/result
→ error analysis
→ engineering decision
```

---
