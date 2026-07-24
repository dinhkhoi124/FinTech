# Evaluation Plan & Failure Taxonomy

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 6, 11.

---

# 6. Evaluation Plan — Minimum Evidence First

Giữ tư duy đánh giá theo layer để biết lỗi nằm ở đâu, nhưng **không bắt buộc triển khai một “evaluation platform 5 tầng” hoàn chỉnh**.

## 6.1 Layer 1 — Intent Classification

### P0

- Accuracy.
- Macro-F1.
- Per-class F1.
- Confusion matrix / top confusion pairs.
- Manual error analysis trên một số case đại diện.

### P1

- Calibration.
- Risk-coverage.
- OOS/OOD AUROC/AUPR.
- Extended slicing.

## 6.2 Layer 2 — Retrieval

### P0 — chỉ 2 experiment chính

```text
R0: approved-only retrieval, không dùng intent
vs
R1: approved-only + intent-aware retrieval
```

Giữ cố định corpus, embedding/index, chunking và top-k để isolate tác động của intent signal.

Metrics bắt buộc:

- Recall@K hoặc Hit@K.
- MRR nếu gold evidence có ranking rõ.
- Wrong-status leakage rate — target = 0.
- Một bảng retrieval error analysis.

### P1

- Variant thứ ba hybrid/reranker.
- nDCG.
- Chunk strategy comparison.
- Embedding model comparison.
- Top-k sensitivity.

## 6.3 Layer 3 — Grounded Generation

### P0

Trên một **critical set nhỏ, review được thủ công**:

- Citation correctness.
- Unsupported factual claim rate.
- Answer/Abstain correctness.

Không bắt buộc cùng lúc triển khai đầy đủ:

```text
Relevance + Faithfulness + Correctness + Completeness
+ Citation Coverage + LLM-as-judge + NLI checker
```

### P1

- Automated faithfulness evaluator.
- Answer relevance/completeness.
- LLM-as-judge hoặc NLI-based checker.

## 6.4 Layer 4 — Safety / Policy Compliance

### P0

- Draft leakage rate.
- Expired-policy usage rate.
- Unsupported answer rate.
- Correct abstention trên no-evidence cases.

Critical invariants:

```text
DRAFT/EXPIRED leakage = 0
No approved evidence → no factual answer
```

### P1

- Escalation precision/recall.
- Prompt-injection suite lớn.
- Risk-weighted safety score.

## 6.5 Layer 5 — End-to-End

### P0

Phân loại mỗi query thành:

```text
Safe Correct Answer
Safe Abstain/Escalate
Wrong Answer
Wrong Abstain/Escalate
System Error
```

Hai metric chính:

1. **Safe Resolution Rate**
2. **Unsafe / Unsupported Answer Rate**

Không cần xây dashboard hay observability metric suite đầy đủ.

## 6.6 Golden Evaluation Set

### P0

Một eval set **nhỏ nhưng gold evidence đáng tin**, ưu tiên khoảng **60–100 queries** cho RAG subset, gồm:

- normal;
- intent-confusion;
- hard-negative;
- no-answer;
- draft-only / expired-only;
- policy-conflict;
- ambiguous hoặc OOS ở mức tối thiểu.

Mỗi query phải có tối thiểu:

```text
gold_intent
expected_response_type
gold_evidence_ids hoặc no_evidence
```

### P1

Mở rộng thêm:

- prompt-injection-like;
- multi-intent;
- far-OOS;
- larger multilingual slices.

**Nguyên tắc:** chất lượng gold mapping quan trọng hơn số lượng query.

---

# 11. Failure Taxonomy

Dùng taxonomy xuyên suốt để tránh kết luận mơ hồ.

```text
E1: Intent wrong
    → Retrieval wrong
    → Answer wrong

E2: Intent wrong
    → Retrieval correct
    → Answer correct/safe

E3: Intent correct
    → Retrieval wrong
    → Answer wrong or safe abstain

E4: Intent correct
    → Retrieval correct
    → Generation unsupported/hallucinated

E5: Evidence/status invalid
    → Filter catches it
    → Safe abstain/escalation

E6: System uncertain
    → Clarification / abstention / escalation correct

E7: KB/model update regression
    → Detected by evaluation/monitoring
    → Rollback or fix
```

P0 final report phải dùng taxonomy này để phân loại các failure quan trọng được
review và chỉ ra số lượng/tỷ lệ khi mẫu đánh giá đủ đáng tin. Phân rã phần trăm
toàn bộ eval set theo mọi layer E1–E5 là P1, không phải điều kiện P0. P0 vẫn phải
báo cáo các safety/end-to-end metric đã khóa ở Section 6 và không được suy diễn tỷ
lệ khi chưa có evidence.

---
