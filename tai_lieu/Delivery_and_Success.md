# Demo, Deliverables & Definition of Success

> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi chạy lại script sinh tài liệu.

> Nội dung nguyên văn từ các section: 13, 14, 15, 16, 17, 19.

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
