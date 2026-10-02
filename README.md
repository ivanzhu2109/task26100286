# DocuFlow 库存过账组件

纯 Python 库，无外部依赖、无服务端口。单据已完成审批，仅支持执行与作废。

## 用法

```python
from docuflow import DocType, Document, Engine

eng = Engine()
eng.execute(Document("r1", DocType.RECEIPT, "SKU1", "B1", 10, "WH1"))
eng.execute(Document("i1", DocType.ISSUE,   "SKU1", "B1", 8,  "WH1"))
eng.execute(Document("s1", DocType.STOCKTAKE, "SKU1", "B1", 20, "WH1"))  # 盘点=设为实盘值
eng.execute(Document("t1", DocType.TRANSFER, "SKU1", "B1", 4,  "WH1", to_warehouse="WH2"))

eng.void("r1")                      # 不合法时返回 False，状态完全不变
eng.balance("WH1", "SKU1", "B1")    # 当前库存
```

## 规则

- 将所有未作废单据按原执行顺序从零重演，每个历史前缀的每个库存必须非负。
- `execute` / `void` 仅当候选历史满足该性质时成功；失败时库存、历史、作废状态完全不变。
- 盘点是绝对基准（设为实盘值，可为零）；作废盘点会移除该基准，后续单据重新受约束。
- 调拨两端同时生效；库存按 (仓库, 物料, 批次) 核算，初始为零；数量为整数。

## 测试

```bash
python3 -m pytest tests/ -q
```
