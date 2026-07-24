# Business Brief & Research Direction

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 0, 1, 2.

---

# VinSmartFuture — Khối Fintech & Thanh toán | AI/DL Track | Đề tài 13

# PayResolve AI

**Banking Intent Classification & Grounded RAG for Payment Support**

*Fine-grained intent classification, controlled synthetic knowledge generation, approved-source retrieval, grounded response, and safe abstention/escalation.*

**Business Brief · PRD · Research Plan · AI Engineering Workflow · 5-Week Internship Plan**

> **Research Question:** Làm thế nào phân loại fine-grained banking intent và sinh câu trả lời chỉ dựa trên FAQ, Policy và Runbook đã được phê duyệt?

> **Nguyên tắc xuyên suốt:** Correctness → Evaluation → Reliability → Improvement → Complexity.

> **Scope constraint:** 1 AI intern · 5 tuần · ưu tiên depth over breadth. P0 phải có evidence; P1/P2 có thể bỏ mà không làm project thất bại.

---

# 0. Executive Summary

## 0.1 Bài toán

Trong hỗ trợ khách hàng ngân hàng/thanh toán, nhiều câu hỏi có ngữ nghĩa rất gần nhau nhưng thuộc các intent khác nhau, dẫn đến policy, FAQ, runbook hoặc hướng escalation khác nhau.

Ví dụ:

```text
"Transfer is pending"
≠
"Transfer completed but recipient did not receive"
≠
"Transfer was declined"
```

Nếu intent bị phân loại sai, retrieval có thể lấy sai tài liệu. Nếu LLM được phép dựa vào tri thức ngoài nguồn đã duyệt, hệ thống có thể tạo câu trả lời không được policy hỗ trợ.

Project vì vậy tập trung vào hai năng lực cốt lõi:

1. **Fine-grained Banking Intent Classification** — phân biệt chính xác các banking intent dễ nhầm lẫn.
2. **Grounded RAG** — chỉ trả lời khi có evidence từ FAQ/Policy/Runbook hợp lệ; nếu không đủ căn cứ thì abstain, hỏi làm rõ hoặc escalate.

## 0.2 Hệ thống mục tiêu

```text
User / Agent Query
        ↓
Intent Classification
        ↓
Retrieval trên Knowledge Base
        ↓
Approved / Effective Policy Filtering
        ↓
Context + Evidence Validation
        ↓
Grounded LLM Generation
        ↓
Citation / Evidence Check
        ↓
Answer | Ask Clarification | Abstain | Escalate
```

## 0.3 Định vị project

Đây không phải bài tập “ghép classifier + vector database + LLM”.

Project được thiết kế để chứng minh năng lực AI Engineer đi trọn vòng đời:

```text
Problem definition
→ Data understanding
→ Baseline
→ Evaluation
→ Error analysis
→ Synthetic data engineering
→ Retrieval
→ Grounded generation
→ Safety
→ API / Tests / Logging / Versioning
→ Incident debugging
→ Change request / System design
```

## 0.4 Đóng góp chính dự kiến

1. **Fine-grained intent benchmark** trên Banking77 với baseline đáng tin và error analysis.
2. **Controlled Synthetic Banking Knowledge Base** gồm FAQ/Policy/Runbook/Escalation Guide, có version/status và hard-negative cases để đánh giá retrieval + safety.
3. **Intent-aware Grounded RAG**: kiểm tra liệu intent signal có cải thiện retrieval/evidence selection so với retrieval không dùng intent.
4. **Evidence-gated response**: không có approved evidence phù hợp → không tạo factual answer.
5. **Failure propagation analysis**: truy nguyên lỗi cuối cùng đến classifier, retrieval, filtering hay generation.
6. **Production-minded AI service**: test, logging, versioning, regression evaluation, fallback và incident handling.

---

# 1. Pain Point, End User & Business Value

## 1.1 Pain Point

### Pain Point A — Fine-grained intent confusion

Customer query trong banking thường ngắn, mơ hồ và có semantic overlap cao.

Sai intent có thể dẫn đến:

```text
Wrong intent
→ Wrong document
→ Wrong SOP / SLA / policy
→ Wrong answer or wrong escalation
```

### Pain Point B — Ungrounded answers

Một LLM có thể trả lời “nghe hợp lý” nhưng:

- dùng kiến thức ngoài corpus;
- dùng policy draft;
- dùng policy đã expired;
- suy diễn khi evidence không đủ;
- trích dẫn tài liệu không thật sự hỗ trợ claim.

Trong bối cảnh Fintech, một hệ thống tốt không phải là hệ thống trả lời nhiều nhất, mà là hệ thống **biết khi nào được phép trả lời và khi nào phải dừng**.

## 1.2 End User

| Vai trò | Nhu cầu |
|---|---|
| Agent CSKH L1 — Primary | Nhận gợi ý intent, evidence và câu trả lời có nguồn để xử lý nhanh và kiểm tra được |
| Team Leader / QA — Secondary | Audit prediction, retrieved evidence, lỗi hệ thống và knowledge gap |
| Knowledge/Policy Owner — Secondary | Biết tài liệu nào đang được dùng, version nào có hiệu lực, thay đổi KB có gây regression không |
| Khách hàng cuối — Beneficiary | Nhận xử lý nhanh và chính xác hơn qua agent |

## 1.3 Product Positioning

MVP là **Agent Copilot / Research Prototype**, không phải autonomous banking chatbot.

Human-in-the-loop được giữ vì:

- hạn chế rủi ro policy/compliance;
- phù hợp scope internship;
- cho phép tập trung đánh giá correctness, grounding và failure modes thay vì xây full product.

---

# 2. Research Direction

## 2.1 Main Research Question

> **Làm thế nào phân loại fine-grained banking intent và sinh câu trả lời chỉ dựa trên FAQ, Policy và Runbook đã được phê duyệt?**

## 2.2 Sub-Research Questions

### RQ1 — Fine-grained Intent Classification

Các intent banking có semantic overlap cao có thể được phân loại chính xác đến đâu bằng một pipeline được xây từ baseline đơn giản đến semantic/model-based approach?

Cần trả lời bằng:

- Accuracy.
- Macro-F1.
- Per-class Precision/Recall/F1.
- Confusion matrix.
- Error analysis trên các intent pair dễ nhầm.
- Low-confidence / ambiguous query analysis.

### RQ2 — Synthetic Knowledge Base as a Research/Data Contribution

Làm thế nào xây một synthetic banking KB đủ kiểm soát để:

- cover các intent mục tiêu;
- có approved/draft/expired versions;
- có hard negatives;
- có evidence mapping rõ ràng;
- cho phép đánh giá retrieval và safety reproducibly?

Synthetic KB không chỉ là dữ liệu “để demo RAG”, mà là **một dataset artifact có specification, versioning, quality checks và evaluation mapping**.

### RQ3 — Intent-aware Retrieval

Việc sử dụng predicted intent như một retrieval signal có cải thiện việc lấy đúng approved evidence so với retrieval không dùng intent hay không?

So sánh P0 tối thiểu, với approved/effective filtering là invariant chung:

```text
R0: approved-only retrieval, không dùng intent
vs
R1: approved-only + intent-aware retrieval
```

Hybrid/reranker hoặc retrieval variant thứ ba là P1 và chỉ mở khi R0/R1 đã
reproducible, có error analysis chỉ ra failure cụ thể cần giải quyết.

Đánh giá bằng:

- Recall@K / Hit Rate@K.
- MRR hoặc nDCG nếu phù hợp.
- Evidence coverage.
- Wrong-status retrieval rate.
- Retrieval latency.

### RQ4 — Grounded Generation & Safe Decision

Evidence gating có giúp giảm unsupported answers trong khi vẫn giữ mức answer coverage hợp lý không?

Hệ thống phải hỗ trợ:

```text
Answer
Ask Clarification
Abstain
Escalate
```

Không được ép model tạo câu trả lời khi evidence không đủ.

## 2.3 Research Hypotheses

| ID | Hypothesis | Evaluation |
|---|---|---|
| H1 | Semantic/model-based intent classifier cải thiện fine-grained classification so với lexical baseline | Macro-F1, per-class F1, confusion pairs |
| H2 | Intent-aware retrieval cải thiện evidence retrieval so với retrieval không dùng intent | Recall@K, MRR/Hit Rate, wrong-evidence rate |
| H3 | Approved-only metadata filtering giảm retrieval leakage từ draft/expired documents | Draft/Expired leakage rate |
| H4 | Evidence-gated generation giảm unsupported answer rate so với always-answer setup | Unsupported Claim Rate, Safe Resolution Rate, Escalation correctness |
| H5 | Failure analysis theo từng layer giúp xác định bottleneck chính xác hơn so với chỉ báo cáo end-to-end accuracy | Error taxonomy + failure propagation report |

---
