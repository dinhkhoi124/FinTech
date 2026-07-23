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

# 3. Scope

## 3.1 Scope dữ liệu

### Intent classification research

- Dataset chính: **Banking77**.
- Ưu tiên benchmark đầy đủ 77 intents để giữ đúng bản chất fine-grained intent classification.
- Có thể chọn một subset 15–20 intents liên quan Payment/Transfer/Card/Cash để:
  - xây synthetic KB;
  - làm retrieval/generation benchmark;
  - demo business workflow.

Cách chia này tránh hai cực đoan:

```text
Chỉ 15–20 intents → classifier research bị quá hẹp
Full 77 intents + KB đầy đủ → scope synthetic RAG quá lớn cho 5 tuần
```

### Grounded RAG research

Synthetic KB tập trung vào các intent được chọn để có thể xây dữ liệu sâu, có conflict/version/hard negative thay vì tạo corpus rộng nhưng nông.

## 3.2 Priority Framework — Scope Lock cho 1 người / 5 tuần

Project dùng ba mức ưu tiên. **Chỉ P0 được xem là cam kết bắt buộc của kỳ thực tập.**

| Priority | Ý nghĩa | Quy tắc |
|---|---|---|
| **P0 — Must Prove** | Phải hoàn thành và **chứng minh bằng số liệu / test / artifact** | Không mở P1 nếu P0 của tuần chưa đạt exit criteria |
| **P1 — Stretch** | Có giá trị nhưng chỉ làm khi P0 ổn định và còn thời gian | Có thể bỏ hoàn toàn mà project vẫn được xem là hoàn chỉnh |
| **P2 — Design-only / Backlog** | Chỉ phân tích trade-off hoặc ghi roadmap | Không triển khai trong 5 tuần |

### P0 — Must Prove

Đây là **minimum viable research + engineering evidence**:

1. **Banking77 benchmark**
   - full 77 intents;
   - 1 lexical baseline;
   - 1 semantic/model-based approach;
   - Macro-F1, per-class metrics, confusion/error analysis.

2. **Controlled Synthetic KB**
   - target khoảng **30–40 documents**;
   - chỉ cần cover sâu một subset khoảng **8–12 intent** phù hợp Payment/Transfer/Card/Cash;
   - có `APPROVED / DRAFT / EXPIRED`, version/effective date, hard negatives;
   - có validation và gold evidence mapping cho eval queries.

3. **Retrieval experiment — chỉ 2 biến thể bắt buộc**
   - **R0:** approved-only retrieval không dùng intent;
   - **R1:** approved-only intent-aware retrieval;
   - cùng corpus, cùng embedding/index và cùng top-k để so sánh công bằng.

4. **Grounded generation + safety**
   - answer chỉ từ approved evidence;
   - citation;
   - evidence-insufficient → abstain/escalate;
   - đo unsupported answer rate trên một critical evaluation set nhỏ nhưng chất lượng.

5. **Minimal end-to-end evaluation**
   - classification;
   - retrieval;
   - grounded/safety;
   - end-to-end outcome;
   - không bắt buộc mọi metric nâng cao ở từng layer.

6. **Minimal production-minded service**
   - 1 API endpoint end-to-end;
   - structured output;
   - structured logging;
   - model version + KB/index version;
   - unit tests cho invariant quan trọng;
   - ít nhất 1 integration/E2E regression test.

7. **One incident exercise**
   - inject/reproduce một KB regression;
   - root cause;
   - fix/rollback;
   - thêm regression test.

8. **One change request phân tích sâu**
   - chọn **1 trong 4**: scale, policy update, multilingual, unseen intent;
   - chỉ cần system-design + trade-off reasoning, không triển khai production.

9. **Concise technical report**
   - RQ;
   - setup;
   - kết quả;
   - error analysis;
   - limitations;
   - decision/next steps.

### P1 — Stretch nếu P0 đã ổn

- OOS/OOD detection riêng với threshold/calibration/risk-coverage.
- Retrieval variant thứ ba: hybrid BM25+dense hoặc reranker.
- Chunk-size / embedding-model sensitivity study.
- Automated LLM-as-judge/NLI groundedness evaluator.
- Ask-clarification policy tinh vi hơn.
- UI Streamlit/Gradio.
- Docker, health check, retry/timeout nâng cao.
- Failure propagation E1–E5 đầy đủ trên toàn eval set.
- Change request thứ hai.
- Mở KB coverage lên 15–20 intents nếu chất lượng mapping vẫn đảm bảo.

### P2 — Design-only / Backlog

- 10M queries/day serving architecture implementation.
- Daily policy ingestion production pipeline.
- Full multilingual production rollout.
- Continuous unknown-intent retraining loop.
- Complex MLOps platform.
- Kubernetes/Kafka/Spark/Ray/multi-agent.
- Full observability stack / distributed tracing.

## 3.3 Stop Rules — Cơ chế tự hạ scope

Vì project do **một người tự triển khai trong 5 tuần**, dùng các stop rule sau:

1. **Week 1 chưa có benchmark reproducible → không fine-tune thêm model thứ ba.**
2. **Week 2 chưa có gold evidence mapping tốt → không mở rộng KB hoặc thêm retriever phức tạp.** Dừng ở 24–30 docs chất lượng còn tốt hơn cố đủ 40 docs nhưng gold mapping yếu.
3. **R0 vs R1 chưa chạy ổn → không làm hybrid/reranker.**
4. **Grounded safety chưa đo được → không ưu tiên UI.**
5. **Service P0 chưa trace được version/log → bỏ Docker/advanced observability.**
6. **Không đủ thời gian Week 5 → chỉ chọn 1 change request, các request còn lại ghi backlog.**
7. Khi phải chọn giữa “thêm feature” và “thêm bằng chứng”, ưu tiên:

```text
Reproducible result
> Error analysis
> Regression test
> New feature
```

## 3.4 Non-goals

- Không xây chatbot ngân hàng production thật.
- Không xử lý giao dịch thật hoặc truy vấn tài khoản thật.
- Không dùng PII hoặc tài liệu nội bộ nhạy cảm.
- Không train foundation LLM từ đầu.
- Không xây full MLOps platform.
- Không thêm Kubernetes/Kafka/Spark/multi-agent chỉ để “đủ stack”.
- Không tối ưu frontend phức tạp trước khi evaluation pipeline đáng tin.
- Không thử quá nhiều model/framework nếu không có hypothesis rõ ràng.

---

# 4. AI Engineering Principles

## 4.1 Baseline trước complexity

Mỗi component phải có baseline trước khi thêm giải pháp phức tạp.

Ví dụ:

```text
Intent:
TF-IDF + Logistic Regression
→ semantic embedding/classifier hoặc transformer

Retrieval:
Simple dense/vector retrieval
→ metadata filtering
→ intent-aware retrieval
→ hybrid/reranking nếu có lý do

Generation:
Evidence-only prompt
→ evidence gate
→ citation verification
```

## 4.2 Mỗi experiment phải trả lời một câu hỏi

Không benchmark hàng loạt model chỉ để chọn score cao nhất.

Experiment note nên có dạng:

```text
Hypothesis
→ Setup
→ Metric
→ Result
→ Error analysis
→ Decision
```

## 4.3 Evaluation tách theo layer

Không dùng một con số end-to-end để che lỗi.

Phải biết:

```text
Classifier sai?
Retriever sai?
Metadata filter sai?
Evidence không đủ?
LLM hallucinate?
Escalation policy sai?
```

## 4.4 Bug quan trọng phải trở thành regression test

```text
Reproduce
→ Root cause
→ Fix
→ Regression test
→ Document lesson
```

## 4.5 AI invariants

Các invariant quan trọng:

1. `DRAFT` và `EXPIRED` không được xuất hiện trong grounding context.
2. Không có approved evidence phù hợp → không tạo factual answer.
3. Citation phải trỏ đến evidence thực sự hỗ trợ claim.
4. Model/KB version mới không được làm safety regression vượt threshold đã định nghĩa.
5. Retrieval metric tăng không được đánh đổi bằng unsupported-answer rate tăng không kiểm soát.
6. Test set không được dùng để tune threshold/hyperparameter.

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

# 7. PRD — Product Requirements

## 7.1 Goal

Xây và đánh giá một Agent Copilot prototype có thể:

```text
Query
→ Predict fine-grained intent
→ Retrieve approved evidence
→ Generate evidence-only response
→ Cite source
→ Stop safely when evidence is insufficient
```

## 7.2 User Stories

| ID | User Story | Priority |
|---|---|---|
| U1 | Là agent, tôi thấy predicted intent và confidence để hiểu hệ thống đang routing như thế nào | P0 |
| U2 | Là agent, tôi thấy evidence được retrieve trước khi dùng câu trả lời | P0 |
| U3 | Là agent, tôi chỉ nhận factual answer khi có approved evidence hỗ trợ | P0 |
| U4 | Là agent, khi câu hỏi mơ hồ hoặc thiếu evidence, hệ thống hỏi làm rõ/abstain/escalate thay vì đoán | P0 |
| U5 | Là QA, tôi truy vết được intent, retrieved docs, scores, model version và KB version | P0 |
| U6 | Là QA, tôi chạy regression evaluation khi model hoặc KB thay đổi | P0 |
| U7 | Là knowledge owner, tôi có thể thêm policy version mới mà không làm hệ thống dùng draft/expired | P1 |

## 7.3 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | Reproducible Banking77 preprocessing và locked split | **P0** |
| F2 | 1 lexical baseline cho intent classification | **P0** |
| F3 | 1 semantic/model-based approach để so sánh | **P0** |
| F4 | Macro-F1 + per-class + confusion/error analysis | **P0** |
| F5 | Synthetic KB schema + generation guideline + validation | **P0** |
| F6 | Approved/Draft/Expired + version/effective-date + gold evidence mapping | **P0** |
| F7 | Retrieval R0: approved-only, không dùng intent | **P0** |
| F8 | Retrieval R1: approved-only + intent-aware | **P0** |
| F9 | Grounded generation + citation + evidence gate | **P0** |
| F10 | Minimal automated evaluation cho classification/retrieval/safety/end-to-end | **P0** |
| F11 | 1 API endpoint end-to-end + structured response | **P0** |
| F12 | Structured logs + model/KB/index version | **P0** |
| F13 | Unit tests cho invariants + ít nhất 1 E2E regression test | **P0** |
| F14 | 1 injected incident + postmortem + regression prevention | **P0** |
| F15 | OOS/OOD detection riêng | P1 |
| F16 | Retrieval variant thứ ba: hybrid/reranker | P1 |
| F17 | Streamlit/Gradio UI | P1 |
| F18 | Docker/health check/retry/advanced observability | P1 |
| F19 | Full clarification policy, automated judge, extended ablations | P1 |

## 7.4 Non-functional Requirements

### P0

**Correctness**
- Metric phải reproducible từ code/config/version.
- Locked test không dùng để tune.
- `DRAFT/EXPIRED` không được lọt vào grounding context.

**Safety**
- Approved-source-only.
- Không đủ evidence → không tạo factual answer.

**Traceability**
Mọi final answer phải truy được tối thiểu:

```text
query
→ predicted intent
→ retrieved document IDs
→ selected evidence
→ final answer / abstain
→ model version + KB/index version
```

**Reproducibility**
- Config/version được lưu.
- Data split cố định.
- Eval set P0 được lock trước final run.

### P1

- Request/trace ID đầy đủ.
- Timeout/retry nâng cao.
- Health check.
- Docker.
- UI.
- Full evaluation history/experiment tracking platform.

### Privacy

- Không dùng PII thật.
- Không dùng customer transaction data thật.
- Synthetic/approved public data only.

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

# 12. Acceptance Criteria — P0 Definition of Done

Đây là tiêu chí để coi project **hoàn thành**. P1 không ảnh hưởng Definition of Done.

## P0 — Classification

- Full Banking77.
- 1 lexical baseline + 1 semantic/model-based approach.
- Reproducible split/config.
- Macro-F1 + per-class F1 + confusion/error analysis.
- Không tune trên locked test.

## P0 — Synthetic KB

- Target 30–40 docs cho subset khoảng 8–12 intents; chấp nhận scope-lock 24–30 docs nếu đổi lại gold mapping/validation tốt.
- Có schema/generation guideline.
- Có `APPROVED / DRAFT / EXPIRED`.
- Có version/effective dates.
- Có hard negatives/version conflicts.
- Có validation.
- Có gold evidence mapping.

## P0 — Retrieval

- R0 approved-only baseline.
- R1 approved-only + intent-aware.
- So sánh cùng corpus/index/top-k.
- Có Recall/Hit@K và error analysis.
- Wrong-status leakage = 0 trên eval set.

## P0 — Grounded RAG & Safety

- Answer chỉ dùng supplied approved evidence.
- Citation truy được về document/chunk.
- No approved evidence → no factual answer.
- Có `ANSWER` và `ABSTAIN/ESCALATE`.
- Có unsupported answer rate + abstention correctness.
- Có end-to-end outcome table.

## P0 — Engineering

- 1 runnable API endpoint.
- Structured output + logging.
- Model version + KB/index version.
- Unit tests cho invariants.
- Ít nhất 1 E2E regression test.
- 1 incident được reproduce → fix/rollback → regression test.

## P0 — System Design

- Chọn **1** change request để phân tích sâu.
- Có failure modes, SLO/metric assumptions, trade-offs và rollback/recovery.
- Không bắt buộc triển khai kiến trúc scale.

## P1 — Stretch, không phải Definition of Done

- OOS/OOD detection.
- Retrieval variant thứ ba.
- Reranker/hybrid.
- Automated groundedness evaluator.
- Ask clarification.
- UI/Docker/advanced observability.
- Full E1–E5 failure propagation.
- Change request thứ hai.

---

# 13. Demo Plan — 10–15 Minutes

Demo không chỉ chọn happy path.

## Case 1 — Clear intent

> “My bank transfer is still pending.”

Kỳ vọng:

```text
Correct intent
→ Correct approved evidence
→ Grounded answer
→ Citation
```

## Case 2 — Fine-grained confusion

> “The transfer says completed, but the recipient still hasn’t received it.”

Mục tiêu:

- phân biệt với `pending_transfer`;
- retrieve policy/runbook khác.

## Case 3 — Draft/Expired trap

KB có:

- V1 expired;
- V2 approved;
- V3 draft.

Kỳ vọng:

- chỉ V2 được grounding.

## Case 4 — Missing evidence

Intent nhận đúng nhưng KB không có approved evidence đủ mạnh.

Kỳ vọng:

```text
No answer
→ Abstain / Escalate
```

Đây là case safety quan trọng.

## Case 5 — Ambiguous query

Query có thể thuộc hai intent gần nhau.

Kỳ vọng:

- confidence thấp;
- ask clarification hoặc safe escalation theo policy.

## Case 6 — Incident/regression story

Trình bày ngắn:

```text
KB update
→ regression detected
→ root cause
→ fix/rollback
→ regression test
```

Case này thể hiện năng lực AI Engineer mạnh hơn một demo UI đẹp.

---

# 14. Deliverables Cuối Kỳ — Prioritized

## P0 — 9 artifacts bắt buộc

1. **Intent Classification Benchmark**
   - full Banking77;
   - 2 approaches;
   - metrics + confusion/error analysis.

2. **Synthetic KB v1**
   - 30–40 docs target (scope-lock 24–30 nếu cần);
   - schema/guideline;
   - status/version;
   - validation;
   - gold evidence mapping.

3. **Retrieval Benchmark**
   - R0 approved-only;
   - R1 intent-aware approved-only;
   - metric + error analysis.

4. **Grounded RAG Evaluation**
   - citation correctness;
   - unsupported answer rate;
   - abstention correctness;
   - end-to-end safe outcomes.

5. **Core Experiment/Ablation Note**
   - R0 vs R1;
   - always-answer vs evidence-gated.

6. **Minimal AI Service**
   - `/query`;
   - logs;
   - model/KB/index version;
   - tests.

7. **Incident Postmortem**
   - reproduce;
   - root cause;
   - fix/rollback;
   - regression test.

8. **One Change Request Design Note**
   - chọn 1 trong 4;
   - trade-offs + rollback/recovery.

9. **Concise Technical Report + Demo**
   - tổng hợp claim → evidence → decision;
   - không lặp lại toàn bộ PRD.

## P1 — Stretch artifacts

- OOS/OOD benchmark.
- Retrieval variant thứ ba.
- Automated judge / richer generation eval.
- Full failure propagation report.
- UI.
- Docker/advanced service hardening.
- Change request thứ hai.

## P2 — Không phải deliverable triển khai

- Production-scale architecture implementation.
- Full MLOps.
- Daily policy pipeline production.
- Multilingual rollout.
- Continuous retraining/OOD loop.

**Scope rule:** một artifact P0 có số liệu đáng tin có giá trị hơn ba artifact P1 chỉ chạy demo.

---

# 15. Weekly Mentor Review Format

| Thời điểm | Hoạt động |
|---|---|
| Thứ Hai | Requirement + acceptance criteria |
| Thứ Ba | Intern gửi design/experiment note ngắn trước khi code sâu |
| Thứ Tư | Review thiết kế, hypothesis, metrics |
| Thứ Năm | Hidden edge case / incident / change request |
| Thứ Sáu | Demo + code review + experiment review + retrospective |

Trong review, intern phải có khả năng:

- giải thích quyết định;
- sửa/debug code;
- đọc metric;
- phân biệt root cause theo layer;
- chứng minh fix bằng evaluation/test;
- nói rõ limitation;
- nêu trade-off.

---

# 16. Scorecard Hướng Tới Full-Time AI Engineer Offer

| Nhóm | Trọng số |
|---|---:|
| Data/model correctness + evaluation quality | 25% |
| Python, ML implementation + software engineering | 20% |
| Debugging, testing + incident handling | 20% |
| Learning velocity + phản ứng với feedback | 20% |
| System design, communication + trade-off reasoning | 15% |

Không tối ưu cho:

- số model đã thử;
- số framework đã dùng;
- UI đẹp;
- chatbot trả lời được vài câu demo;
- một con số accuracy cao không có error analysis.

Tối ưu cho tín hiệu:

> **“Giao một bài toán AI mới, intern có thể phân rã, xây baseline, đo đúng, phân tích lỗi, cải thiện có phương pháp, productionize, debug và giải thích trade-off.”**

---

# 17. Definition of Success

Sau 5 tuần, thành công **không** có nghĩa là hoàn thành mọi ý tưởng trong PRD.

Thành công nghĩa là hoàn thành P0 với bằng chứng đủ sâu:

```text
Full Banking77
→ 2 classification baselines
→ error analysis

Focused synthetic KB
→ gold evidence mapping
→ R0 vs R1 retrieval experiment

Grounded generation
→ citation + evidence gate
→ safety/end-to-end metrics

Minimal service
→ logs/version/tests
→ one incident resolved

One change request
→ system design + trade-off reasoning
```

Mentor nên thấy:

> **“Intern biết cắt scope, chọn experiment quan trọng, chứng minh claim bằng số liệu, phát hiện failure, và chuyển kết quả nghiên cứu thành một hệ thống nhỏ có thể test/debug.”**

Không cần thấy:

- 3–5 retrievers;
- nhiều model;
- full UI;
- full MLOps;
- 4 change requests đều triển khai;
- một technical report rất dài nhưng thiếu kết quả định lượng.

Nguyên tắc quyết định cuối cùng:

```text
Depth of evidence
> Breadth of features

P0 complete and defensible
> P0 + P1 half-finished

One strong experiment
> Many weak comparisons
```

---

# 18. Tài liệu tham khảo định hướng

## Research

1. Casanueva, I., Temčinas, T., Gerz, D., Henderson, M., Vulić, I.  
   **Efficient Intent Detection with Dual Sentence Encoders.** NLP4ConvAI 2020.

2. BANKING77 dataset — PolyAI task-specific datasets.

3. Lewis, P. et al.  
   **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.** NeurIPS 2020.

## AI Engineering / Production ML

4. Google — Rules of Machine Learning.

5. Google — Production ML Systems.

6. Google — Monitoring Production ML Pipelines.

7. Google — Deployment Testing for Production ML.

8. Microsoft — RAG End-to-End Evaluation.

9. Microsoft — RAG Evaluators.

10. Microsoft — Observability in Generative AI.

---

# 19. Tóm tắt một câu theo từng tuần

```text
Week 1 — P0:
Full Banking77 + 2 baselines + error analysis.

Week 2 — P0:
Synthetic KB có kiểm soát + R0 vs R1 retrieval.

Week 3 — P0:
Grounded answer/evidence gate + critical safety evaluation.

Week 4 — P0:
Minimal API + logs/version/tests + 1 incident.

Week 5 — P0:
Final evidence + 1 deep change request + concise report/demo.
```

> **PayResolve AI không phải mini AI platform. Đây là một AI system nhỏ, có scope lock rõ ràng, trong đó mỗi claim chính phải được chứng minh bằng experiment, metric hoặc regression test.**

> **P1/P2 chỉ được mở sau khi P0 đã hoàn thành.**
