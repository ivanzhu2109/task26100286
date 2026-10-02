"""DocuFlow 单据类型定义（骨架）。"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional


class DocType(enum.Enum):
    RECEIPT = "receipt"      # 收货
    ISSUE = "issue"          # 发货
    TRANSFER = "transfer"    # 调拨
    STOCKTAKE = "stocktake"  # 盘点


@dataclass(frozen=True)
class Document:
    """一张已审批、待执行的单据。每张单据只涉及一个物料批次。"""

    doc_id: str
    doc_type: DocType
    sku: str
    batch: str
    quantity: int
    warehouse: str
    # 仅调拨使用：目标仓库
    to_warehouse: Optional[str] = None
