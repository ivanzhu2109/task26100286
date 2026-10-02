"""DocuFlow 引擎测试。"""
from docuflow import DocType, Document, Engine

W1, W2 = "WH1", "WH2"
SKU, BATCH = "SKU1", "B1"


def receipt(doc_id, qty, wh=W1):
    return Document(doc_id, DocType.RECEIPT, SKU, BATCH, qty, wh)


def issue(doc_id, qty, wh=W1):
    return Document(doc_id, DocType.ISSUE, SKU, BATCH, qty, wh)


def transfer(doc_id, qty, src=W1, dst=W2):
    return Document(doc_id, DocType.TRANSFER, SKU, BATCH, qty, src, to_warehouse=dst)


def stocktake(doc_id, qty, wh=W1):
    return Document(doc_id, DocType.STOCKTAKE, SKU, BATCH, qty, wh)


def test_required_scenario_void_receipt_blocked_by_intermediate_negative():
    """收货10、发货8、盘点20：作废收货必须失败，即使最终库存仍是20。"""
    eng = Engine()
    assert eng.execute(receipt("r1", 10))
    assert eng.execute(issue("i1", 8))
    assert eng.execute(stocktake("s1", 20))
    assert eng.balance(W1, SKU, BATCH) == 20

    # 作废收货后重演：发货8 -> -8（盘点之前出现负库存），非法
    assert not eng.void("r1")
    # 失败必须保持库存、历史及作废状态完全不变
    assert eng.balance(W1, SKU, BATCH) == 20
    assert eng.void("s1")  # 仍可正常作废盘点：收货10-发货8=2 非负
    assert eng.balance(W1, SKU, BATCH) == 2


def test_required_scenario_void_receipt_ok_then_void_stocktake_fails():
    """收货10、盘点5、发货3：作废收货成功余额仍是2；随后作废盘点失败。"""
    eng = Engine()
    assert eng.execute(receipt("r1", 10))
    assert eng.execute(stocktake("s1", 5))
    assert eng.execute(issue("i1", 3))
    assert eng.balance(W1, SKU, BATCH) == 2

    # 作废收货：盘点5是绝对基准，不再依赖更早的收货 -> 5-3=2
    assert eng.void("r1")
    assert eng.balance(W1, SKU, BATCH) == 2

    # 再作废盘点：基准被移除，发货3 -> -3，非法
    assert not eng.void("s1")
    assert eng.balance(W1, SKU, BATCH) == 2


def test_execute_failure_keeps_state():
    eng = Engine()
    assert eng.execute(receipt("r1", 5))
    assert not eng.execute(issue("i1", 6))  # 5-6=-1 非法
    assert eng.balance(W1, SKU, BATCH) == 5
    assert eng.execute(issue("i2", 5))
    assert eng.balance(W1, SKU, BATCH) == 0


def test_transfer_atomic_and_per_warehouse():
    eng = Engine()
    assert eng.execute(receipt("r1", 10))
    assert not eng.execute(transfer("t0", 11))  # 源仓库不够，整体不生效
    assert eng.execute(transfer("t1", 4))
    assert eng.balance(W1, SKU, BATCH) == 6
    assert eng.balance(W2, SKU, BATCH) == 4
    # 作废调拨后两端一起回退
    assert eng.void("t1")
    assert eng.balance(W1, SKU, BATCH) == 10
    assert eng.balance(W2, SKU, BATCH) == 0


def test_stocktake_zero_and_not_a_delta():
    eng = Engine()
    assert eng.execute(receipt("r1", 10))
    assert eng.execute(stocktake("s1", 0))  # 实盘可为零，设为0而非减10
    assert eng.balance(W1, SKU, BATCH) == 0
    assert eng.execute(receipt("r2", 3))
    assert eng.execute(stocktake("s2", 7))  # 盘点是绝对值，不是加减差额
    assert eng.balance(W1, SKU, BATCH) == 7


def test_void_unknown_or_already_voided():
    eng = Engine()
    assert eng.execute(receipt("r1", 5))
    assert not eng.void("nope")
    assert eng.void("r1")
    assert not eng.void("r1")  # 不能重复作废
    assert eng.balance(W1, SKU, BATCH) == 0


def test_invalid_documents_rejected():
    eng = Engine()
    assert not eng.execute(receipt("r0", 0))     # 收货数量必须为正
    assert not eng.execute(issue("i0", -1))      # 发货数量必须为正
    assert not eng.execute(stocktake("s0", -1))  # 实盘不能为负
    assert not eng.execute(Document("t0", DocType.TRANSFER, SKU, BATCH, 1, W1))  # 缺目标仓
    assert not eng.execute(transfer("t1", 1, W1, W1))  # 同仓调拨
    assert eng.balance(W1, SKU, BATCH) == 0


def test_duplicate_doc_id_rejected():
    eng = Engine()
    assert eng.execute(receipt("r1", 5))
    assert not eng.execute(receipt("r1", 5))
    assert eng.balance(W1, SKU, BATCH) == 5


def test_stocktake_does_not_absolve_earlier_negative():
    """盘点之后的库存不依赖更早收发货，但盘点之前的负库存仍非法。"""
    eng = Engine()
    assert eng.execute(receipt("r1", 2))
    # 先发货5再盘点10：中间前缀 2-5=-3 非法，即使盘点后为正
    assert not eng.execute(issue("i1", 5))
    assert eng.execute(issue("i1", 2))
    assert eng.execute(stocktake("s1", 10))
    assert eng.balance(W1, SKU, BATCH) == 10


def test_void_makes_later_execute_possible():
    eng = Engine()
    assert eng.execute(receipt("r1", 10))
    assert eng.execute(issue("i1", 10))
    assert not eng.execute(issue("i2", 1))
    assert eng.void("i1")
    assert eng.execute(issue("i2", 1))
    assert eng.balance(W1, SKU, BATCH) == 9
