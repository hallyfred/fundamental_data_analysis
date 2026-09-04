from config.config import build_ticker_batches, enumerate_ticker_batches, get_batch_for_day


def test_build_and_enumerate_ticker_batches():
    symbols = ["A", "B", "C", "D", "E", "F", "G"]
    assert build_ticker_batches(symbols, batch_size=5) == [["A", "B", "C", "D", "E"], ["F", "G"]]
    assert enumerate_ticker_batches(["A", "B", "C", "D"], batch_size=2) == [(0, ["A", "B"]), (1, ["C", "D"])]


def test_get_batch_for_day_rotation():
    assert get_batch_for_day(day_index=2, symbols=["A", "B", "C", "D", "E"], batch_size=2) == ["E"]
