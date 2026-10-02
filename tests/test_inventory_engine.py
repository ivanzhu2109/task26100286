import unittest

from docuflow import DocType, Document, InventoryEngine


def rece(doc_id, wh="w1", qty=10, sku="sku", batch="b"):
    return Document(doc_id, DocType.RECE, sku, batch, wh, qty)


def issue(doc_id, wh="w1", qty=1, sku="sku", batch="b"):
    return Document(doc_id, DocType.ISSUE, sku, batch, wh, qty)


def stocktake(doc_id, wh="w1", qty=0, sku="sku", batch="b"):
    return Document(doc_id, DocType.STOCKTAKE, sku, batch, wh, qty)


def transfer(doc_id, src="w1", dst="w2", qty=1, sku="sku", batch="b"):
    return Document(doc_id, DocType.TRANSFER, sku, batch, src, qty, to_warehouse=dst)


class RequiredScenariosTest(unittest.TestCase):
    def test_void_receive_after_stocktake_fails(self):
        # 收货10、发货8、盘点20：作废收货必须失败，即使最终库存仍是20
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=10)))
        self.assertTrue(e.execute(issue("i1", qty=8)))
        self.assertTrue(e.execute(stocktake("s1", qty=20)))
        self.assertFalse(e.void("r1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 20)
        # 失败后作废状态不变：再次作废仍应尝试同一语义而非报"已作废"
        self.assertFalse(e.void("r1"))
        self.assertTrue(e.void("s1"))  # 盘点本身仍可作废
        self.assertEqual(e.balance("w1", "sku", "b"), 2)

    def test_void_receive_then_stocktake(self):
        # 收货10、盘点5、发货3：作废收货成功，余额仍是2；随后作废盘点失败
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=10)))
        self.assertTrue(e.execute(stocktake("s1", qty=5)))
        self.assertTrue(e.execute(issue("i1", qty=3)))
        self.assertTrue(e.void("r1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 2)
        self.assertFalse(e.void("s1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 2)


class ExecuteTest(unittest.TestCase):
    def test_issue_without_stock_fails_and_keeps_state(self):
        e = InventoryEngine()
        self.assertFalse(e.execute(issue("i1", qty=1)))
        self.assertEqual(e.balance("w1", "sku", "b"), 0)
        self.assertFalse(e.void("i1"))  # 未进入历史

    def test_stocktake_sets_absolute_value(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=10)))
        self.assertTrue(e.execute(stocktake("s1", qty=4)))
        self.assertEqual(e.balance("w1", "sku", "b"), 4)
        self.assertTrue(e.execute(stocktake("s2", qty=0)))
        self.assertEqual(e.balance("w1", "sku", "b"), 0)

    def test_duplicate_doc_id_rejected(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=5)))
        self.assertFalse(e.execute(rece("r1", qty=7)))
        self.assertEqual(e.balance("w1", "sku", "b"), 5)

    def test_transfer_moves_atomically(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", wh="w1", qty=6)))
        self.assertFalse(e.execute(transfer("t1", qty=7)))  # 源仓不足，两端都不变
        self.assertEqual(e.balance("w1", "sku", "b"), 6)
        self.assertEqual(e.balance("w2", "sku", "b"), 0)
        self.assertTrue(e.execute(transfer("t1", qty=6)))
        self.assertEqual(e.balance("w1", "sku", "b"), 0)
        self.assertEqual(e.balance("w2", "sku", "b"), 6)

    def test_stock_isolated_by_warehouse_sku_batch(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", wh="w1", qty=3, sku="a", batch="b1")))
        self.assertTrue(e.execute(rece("r2", wh="w1", qty=4, sku="a", batch="b2")))
        self.assertFalse(e.execute(issue("i1", wh="w1", qty=1, sku="a", batch="b3")))
        self.assertEqual(e.balance("w1", "a", "b1"), 3)
        self.assertEqual(e.balance("w1", "a", "b2"), 4)
        self.assertEqual(e.balance("w1", "a", "b3"), 0)


class VoidTest(unittest.TestCase):
    def test_void_unknown_or_already_voided(self):
        e = InventoryEngine()
        self.assertFalse(e.void("nope"))
        self.assertTrue(e.execute(rece("r1", qty=5)))
        self.assertTrue(e.void("r1"))
        self.assertFalse(e.void("r1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 0)

    def test_void_middle_doc_replays_remaining_in_order(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=10)))
        self.assertTrue(e.execute(issue("i1", qty=4)))
        self.assertTrue(e.execute(rece("r2", qty=2)))
        self.assertTrue(e.void("i1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 12)

    def test_failed_void_keeps_history_and_stock(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", qty=5)))
        self.assertTrue(e.execute(issue("i1", qty=5)))
        self.assertFalse(e.void("r1"))  # 作废后发货将产生负库存
        self.assertEqual(e.balance("w1", "sku", "b"), 0)
        self.assertTrue(e.void("i1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 5)

    def test_void_transfer_restores_both_sides(self):
        e = InventoryEngine()
        self.assertTrue(e.execute(rece("r1", wh="w1", qty=5)))
        self.assertTrue(e.execute(transfer("t1", qty=5)))
        self.assertTrue(e.void("t1"))
        self.assertEqual(e.balance("w1", "sku", "b"), 5)
        self.assertEqual(e.balance("w2", "sku", "b"), 0)


if __name__ == "__main__":
    unittest.main()
