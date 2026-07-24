# Scope, Principles & Product Requirements

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 3, 4, 7, 12.

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
