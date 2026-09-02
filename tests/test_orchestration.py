from config.config import build_ticker_batches, enumerate_ticker_batches, get_batch_for_day


def test_build_ticker_batches_groups_symbols_in_order():
    symbols = ["A", "B", "C", "D", "E", "F", "G"]
    batches = build_ticker_batches(symbols, batch_size=5)

    assert batches == [["A", "B", "C", "D", "E"], ["F", "G"]]


def test_enumerate_batches_keeps_order_and_index():
    batches = enumerate_ticker_batches(["A", "B", "C", "D", "E", "F"], batch_size=3)
    assert batches == [
        (0, ["A", "B", "C"]),
        (1, ["D", "E", "F"]),
    ]


def test_get_batch_for_day_rotates_using_day_index():
    symbols = ["A", "B", "C", "D", "E", "F", "G"]
    assert get_batch_for_day(day_index=2, symbols=symbols, batch_size=3) == ["G"]
