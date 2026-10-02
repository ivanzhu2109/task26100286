"""DocuFlow 库存过账引擎。"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .types import DocType, Document

StockKey = Tuple[str, str, str]  # (warehouse, sku, batch)


def _apply(doc: Document, stock: Dict[StockKey, int]) -> None:
    key = (doc.warehouse, doc.sku, doc.batch)
    if doc.doc_type is DocType.RECE:
        stock[key] = stock.get(key, 0) + doc.quantity
    elif doc.doc_type is DocType.ISSUE:
        stock[key] = stock.get(key, 0) - doc.quantity
    elif doc.doc_type is DocType.TRANSFER:
        target = (doc.to_warehouse, doc.sku, doc.batch)
        stock[key] = stock.get(key, 0) - doc.quantity
        stock[target] = stock.get(target, 0) + doc.quantity
    elif doc.doc_type is DocType.STOCKTAKE:
        stock[key] = doc.quantity
    else:  # pragma: no cover
        raise ValueError(f"unknown doc type: {doc.doc_type}")


def _replay(docs: List[Document]) -> Optional[Dict[StockKey, int]]:
    """从零重演候选历史；任一前缀出现负库存则返回 None。"""
    stock: Dict[StockKey, int] = {}
    for doc in docs:
        _apply(doc, stock)
        if any(qty < 0 for qty in stock.values()):
            return None
    return stock


class InventoryEngine:
    """库存过账引擎：执行 / 作废 / 查询余额。"""

    def __init__(self) -> None:
        self._history: List[Document] = []
        self._voided: set[str] = set()
        self._stock: Dict[StockKey, int] = {}

    def _active_docs(self) -> List[Document]:
        return [d for d in self._history if d.doc_id not in self._voided]

    def execute(self, doc: Document) -> bool:
        if any(d.doc_id == doc.doc_id for d in self._history):
            return False
        stock = _replay(self._active_docs() + [doc])
        if stock is None:
            return False
        self._history.append(doc)
        self._stock = stock
        return True

    def void(self, doc_id: str) -> bool:
        if doc_id in self._voided:
            return False
        if not any(d.doc_id == doc_id for d in self._history):
            return False
        candidate = [d for d in self._history if d.doc_id != doc_id and d.doc_id not in self._voided]
        stock = _replay(candidate)
        if stock is None:
            return False
        self._voided.add(doc_id)
        self._stock = stock
        return True

    def balance(self, warehouse: str, sku: str, batch: str) -> int:
        return self._stock.get((warehouse, sku, batch), 0)
