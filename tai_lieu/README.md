# Tài liệu đọc riêng — PayResolve AI

Thư mục này chia nội dung của [`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md)
thành các tài liệu ngắn hơn để dễ đọc.

> **Quy tắc nguồn chuẩn:** `docs/MASTER_PRD.md` vẫn là tài liệu authoritative duy
> nhất. Các file ở đây là bản sinh tự động phục vụ đọc, không thay thế master và
> không nên được chỉnh sửa độc lập.

## Mục lục

| File | Nội dung | Section trong master |
|---|---|---:|
| [`Brief.md`](Brief.md) | Business Brief & Research Direction | 0, 1, 2 |
| [`PRD.md`](PRD.md) | Scope, Principles & Product Requirements | 3, 4, 7, 12 |
| [`Data_Strategy.md`](Data_Strategy.md) | Data Strategy | 5 |
| [`Evaluation_Plan.md`](Evaluation_Plan.md) | Evaluation Plan & Failure Taxonomy | 6, 11 |
| [`System_Architecture.md`](System_Architecture.md) | System Architecture & Technology Strategy | 8, 9 |
| [`Internship_Plan.md`](Internship_Plan.md) | 5-Week AI Engineering Workflow | 10 |
| [`Delivery_and_Success.md`](Delivery_and_Success.md) | Demo, Deliverables & Definition of Success | 13, 14, 15, 16, 17, 19 |
| [`References.md`](References.md) | References | 18 |

## Cập nhật bản đọc

Chạy từ thư mục gốc repository:

```powershell
py -3.11 scripts/reporting/split_master_prd.py --root .
```

Kiểm tra mà không ghi file:

```powershell
py -3.11 scripts/reporting/split_master_prd.py --root . --check
```
