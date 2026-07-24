# Data Strategy

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 5.

---

# 5. Data Strategy

## 5.1 Banking77

### Data audit bắt buộc

- Class distribution.
- Duplicate / near-duplicate.
- Train-test leakage risk.
- Short/ambiguous queries.
- Semantic overlap giữa intents.
- Potential label anomalies.
- Confusion-prone intent pairs.

### Data split

```text
Train
Validation
Locked Test
```

Quy tắc:

- Hyperparameter tune trên validation.
- Confidence/evidence threshold tune trên validation.
- Locked test dùng cho final evaluation.
- Không “nhìn test rồi chỉnh model”.

## 5.2 Synthetic Banking Knowledge Base

### Mục tiêu

Khoảng **30–40+ documents có kiểm soát**, không phải hàng trăm document sinh tự do.

Loại tài liệu:

- FAQ.
- Policy.
- Runbook.
- Escalation Guide.

Status:

```text
APPROVED
DRAFT
EXPIRED
```

### Schema tối thiểu

```json
{
  "document_id": "POLICY_TRANSFER_001",
  "title": "Pending Transfer Policy",
  "document_type": "policy",
  "intent_scope": ["pending_transfer"],
  "product": "bank_transfer",
  "status": "APPROVED",
  "version": "1.3",
  "effective_date": "2026-01-01",
  "expiry_date": null,
  "approved_by": "Synthetic Policy Owner",
  "source_type": "synthetic",
  "risk_level": "medium",
  "content": "..."
}
```

### KB phải có intentional test cases

1. Approved document đúng intent.
2. Approved document gần nghĩa nhưng sai intent.
3. Draft document có wording rất giống đáp án đúng.
4. Expired document từng đúng nhưng không còn hiệu lực.
5. Approved và expired version có khác biệt policy.
6. Hai intent có wording gần nhau nhưng runbook khác nhau.
7. Intent có FAQ nhưng thiếu policy đủ để trả lời.
8. Không có evidence phù hợp.
9. Multi-document answer cần tổng hợp evidence.
10. Conflict/ambiguity cần abstain hoặc escalate.

### Quality controls

Synthetic generation phải có:

- generation guideline;
- schema validation;
- deterministic IDs;
- status/version consistency;
- intent coverage matrix;
- duplicate/near-duplicate audit;
- contradiction review;
- source-to-query evidence mapping;
- dataset versioning.

## 5.3 Leakage control

Không được tạo evaluation query bằng cách paraphrase trực tiếp đúng câu trong tài liệu rồi dùng chính query đó để tune retrieval.

Nên tách:

```text
KB generation
→ Gold query generation/review
→ Locked evaluation mapping
```

Mỗi query trong retrieval eval phải có:

- expected intent;
- expected evidence document/chunk;
- expected action: answer / clarify / abstain / escalate.

---
