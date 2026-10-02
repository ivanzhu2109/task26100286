"""DocuFlow 单据类型定义。"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional


class DocType(enum.Enum):
    RECE = "receive"
    ISSUE = "issue"
    TRANSFER = "transfer"
    STOCKTAKE = "stocktake"


@dataclass(frozen=True)
class Document:
    """一张已审批、待执行的单据。每张单据只涉及一个物料批次。"""

    doc_id: str
    doc_type: DocType
    sku: str
    batch: str
    warehouse: str
    quantity: int
    to_warehouse: Optional[str] = None

    def __post_init__(self) -> None:
        if self.doc_type in (DocType.RECE, DocType.ISSUE, DocType.TRANSFER):
            if self.quantity <= 0:
                raise ValueError("receive/issue/transfer quantity must be positive")
        if self.doc_type is DocType.STOCKTAKE and self.quantity < 0:
            raise ValueError("stocktake quantity must be non-negative")
        if self.doc_type is DocType.TRANSFER:
            if not self.to_warehouse:
                raise ValueError("transfer requires to_warehouse")
            if self.to_warehouse == self.warehouse:
                raise ValueError("transfer source and target must differ")
