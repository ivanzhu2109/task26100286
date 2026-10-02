# task26100286

DocuFlow 单据引擎 —— 库存过账组件（纯 Python，无外部依赖）。

## 用法

```python
from docuflow import InventoryEngine, Document, DocType

engine = InventoryEngine()
engine.execute(Document("r1", DocType.RECE, "sku", "batch1", "w1", 10))
engine.execute(Document("s1", DocType.STOCKTAKE, "sku", "batch1", "w1", 5))
engine.void("r1")                       # 作废历史单据，重演校验
engine.balance("w1", "sku", "batch1")   # -> 5
```

- `execute(doc)` / `void(doc_id)` 返回 `bool`：仅当未作废单据按原顺序从零重演后
  每个历史前缀的所有库存均非负时成功；失败时库存、历史、作废状态完全不变。
- 调拨单需传 `to_warehouse`，扣减与增加原子生效。
- 盘点将对应 (仓库, 物料, 批次) 库存设为实盘值。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
