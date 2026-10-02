"""DocuFlow 库存过账引擎。

核心规则：将所有未作废单据按原执行顺序从零重演，
每个历史前缀的每个库存都必须非负。
执行 / 作废仅当候选历史满足该性质时成功，失败时状态完全不变。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .documents import DocType, Document

Key = Tuple[str, str, str]  # (warehouse, sku, batch)


class Engine:
    """库存过账引擎：执行 / 作废 / 查询余额。"""

    def __init__(self) -> None:
        self._history: List[Document] = []  # 已执行单据，按执行顺序
        self._voided: Set[str] = set()      # 已作废的单据 ID
        self._balances: Dict[Key, int] = {} # 当前库存（由重演推导）

    # ---- 公开操作 ----

    def execute(self, doc: Document) -> bool:
        """执行单据。候选历史不合法时返回 False 且状态不变。"""
        if not self._is_valid_doc(doc):
            return False
        if any(d.doc_id == doc.doc_id for d in self._history):
            return False  # 单据 ID 必须唯一
        candidate = self._history + [doc]
        balances = self._replay(candidate, self._voided)
        if balances is None:
            return False
        self._history.append(doc)
        self._balances = balances
        return True

    def void(self, doc_id: str) -> bool:
        """作废一张已执行且未作废的单据。不合法时返回 False 且状态不变。"""
        if doc_id in self._voided:
            return False
        if not any(d.doc_id == doc_id for d in self._history):
            return False
        candidate_voided = self._voided | {doc_id}
        balances = self._replay(self._history, candidate_voided)
        if balances is None:
            return False
        self._voided = candidate_voided
        self._balances = balances
        return True

    def balance(self, warehouse: str, sku: str, batch: str) -> int:
        """返回当前库存。"""
        return self._balances.get((warehouse, sku, batch), 0)

    # ---- 内部 ----

    @staticmethod
    def _is_valid_doc(doc: Document) -> bool:
        if doc.doc_type is DocType.STOCKTAKE:
            return doc.quantity >= 0  # 实盘数量可为零
        if doc.quantity <= 0:
            return False  # 收货 / 发货 / 调拨数量为正
        if doc.doc_type is DocType.TRANSFER:
            return doc.to_warehouse is not None and doc.to_warehouse != doc.warehouse
        return doc.doc_type in (DocType.RECEIPT, DocType.ISSUE)

    @staticmethod
    def _replay(history: List[Document], voided: Set[str]) -> Optional[Dict[Key, int]]:
        """从零重演未作废单据；任一前缀出现负库存则返回 None。"""
        balances: Dict[Key, int] = {}
        for doc in history:
            if doc.doc_id in voided:
                continue
            Engine._apply(balances, doc)
            if any(v < 0 for v in balances.values()):
                return None
        return balances

    @staticmethod
    def _apply(balances: Dict[Key, int], doc: Document) -> None:
        key = (doc.warehouse, doc.sku, doc.batch)
        if doc.doc_type is DocType.RECEIPT:
            balances[key] = balances.get(key, 0) + doc.quantity
        elif doc.doc_type is DocType.ISSUE:
            balances[key] = balances.get(key, 0) - doc.quantity
        elif doc.doc_type is DocType.TRANSFER:
            dst = (doc.to_warehouse, doc.sku, doc.batch)  # type: ignore[misc]
            # 两端必须一起生效
            balances[key] = balances.get(key, 0) - doc.quantity
            balances[dst] = balances.get(dst, 0) + doc.quantity
        elif doc.doc_type is DocType.STOCKTAKE:
            balances[key] = doc.quantity  # 绝对基准，不是加减差额
