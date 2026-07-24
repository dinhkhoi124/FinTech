# System Architecture & Technology Strategy

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 8, 9.

---

# 8. System Architecture

## 8.1 Core Pipeline

```text
Client / Agent UI
        ↓
API Layer
        ↓
Input Validation
        ↓
Intent Classifier
        ↓
Intent + Confidence
        ↓
Retriever
   ├─ Vector/Sparse Index
   └─ Metadata Filter
        ↓
Approved Evidence Set
        ↓
Evidence Sufficiency Check
   ├─ insufficient → Clarify / Abstain / Escalate
   └─ sufficient
        ↓
Grounded LLM
        ↓
Citation / Claim Check
        ↓
Structured Response
        ↓
Audit Log / Evaluation Trace
```

## 8.2 Retrieval variants for research

### P0 — R0: Approved-only baseline

```text
Query
→ Retriever
→ Filter APPROVED + effective
→ Top-K evidence
```

Đây là baseline an toàn. Status filtering là invariant, **không phải feature tùy chọn**.

### P0 — R1: Intent-aware approved retrieval

```text
Query
→ Predicted intent
→ intent-conditioned filter/boost
→ Filter APPROVED + effective
→ Top-K evidence
```

So sánh R0 vs R1 để trả lời trực tiếp RQ:

> Intent signal có cải thiện retrieval quality không?

### P1 — R2: Hybrid / Reranked retrieval

Chỉ thêm khi R0 và R1 đã reproducible và có error analysis cho thấy lexical+dense combination hoặc reranking có khả năng giải quyết failure cụ thể.

Không được thêm R2 chỉ để “đủ 3 variant”.

## 8.3 Grounded Generation Contract

LLM nhận:

- user query;
- predicted intent nếu cần;
- approved evidence;
- strict generation rules.

Rule tối thiểu:

```text
Use only supplied evidence.
Do not use external banking knowledge.
Do not invent fees, timelines, eligibility, policy or status.
Cite supporting evidence for factual claims.
If evidence is insufficient or conflicting, do not guess.
Return clarification, abstention or escalation.
```

## 8.4 Structured Output

```json
{
  "request_id": "req_001",
  "intent": "pending_transfer",
  "intent_confidence": 0.91,
  "response_type": "answer",
  "answer": "Synthetic grounded response...",
  "citations": [
    {
      "document_id": "POLICY_TRANSFER_001",
      "version": "1.3",
      "section": "3.2"
    }
  ],
  "grounded": true,
  "escalate": false,
  "reason": null,
  "model_version": "intent_v2",
  "kb_version": "kb_v3"
}
```

Trường hợp không đủ evidence:

```json
{
  "request_id": "req_002",
  "intent": "pending_transfer",
  "intent_confidence": 0.72,
  "response_type": "escalate",
  "answer": null,
  "citations": [],
  "grounded": false,
  "escalate": true,
  "reason": "No approved evidence sufficiently supports the request."
}
```

---

# 9. Technology Strategy

## 9.1 Core stack

Ưu tiên công cụ tối thiểu đủ để chứng minh engineering quality:

```text
Python
Git
pytest
pandas
scikit-learn
PyTorch / Transformers / Sentence Transformers khi cần
FAISS hoặc vector search tương đương
FastAPI hoặc API layer tương đương
JSON / JSONL / CSV / Markdown
```

## 9.2 Optional tools

Chỉ dùng khi giải quyết vấn đề cụ thể:

```text
MLflow / Weights & Biases
Docker
BM25 / hybrid retrieval
Reranker
Qdrant / Chroma / pgvector
Streamlit / Gradio
LangChain / LlamaIndex
```

## 9.3 Không khóa cứng model từ đầu

Không đặt requirement rằng “bắt buộc USE + MLP” hay “bắt buộc model X”.

Quy trình đúng:

```text
Simple baseline
→ semantic baseline/model
→ error analysis
→ evidence-based model choice
```

Model được chọn phải trả lời được:

- tốt hơn baseline ở đâu?
- lỗi còn lại là gì?
- latency/cost có phù hợp không?
- complexity tăng có đáng không?

---
