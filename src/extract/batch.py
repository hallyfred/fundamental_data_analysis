from __future__ import annotations

from dataclasses import dataclass, field


class ExtractionBatchError(RuntimeError):
    """Raised when an endpoint does not complete every ticker in its batch."""


@dataclass
class ExtractionBatch:
    endpoint: str
    symbols: list[str]
    run_id: str | None = None
    completed_symbols: list[str] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)
    stopped_early: bool = False

    def record_success(self, symbol: str) -> None:
        if symbol not in self.completed_symbols:
            self.completed_symbols.append(symbol)

    def record_failure(self, symbol: str, error: Exception | str, *, stop: bool = False) -> None:
        self.failures[symbol] = str(error)
        self.stopped_early = self.stopped_early or stop

    @property
    def pending_symbols(self) -> list[str]:
        processed = set(self.completed_symbols) | set(self.failures)
        return [symbol for symbol in self.symbols if symbol not in processed]

    @property
    def status(self) -> str:
        return "SUCCESS" if not self.failures and not self.pending_symbols else "ERROR"

    def as_log_entry(self) -> dict:
        return {
            "run_id": self.run_id,
            "endpoint": self.endpoint,
            "status": self.status,
            "planned_symbols": self.symbols,
            "completed_symbols": self.completed_symbols,
            "failed_symbols": list(self.failures),
            "pending_symbols": self.pending_symbols,
            "failure_reasons": self.failures,
            "planned_requests": len(self.symbols),
            "stopped_early": self.stopped_early,
        }

    def raise_for_incomplete_batch(self) -> None:
        if self.status == "SUCCESS":
            return

        failed = ", ".join(self.failures) or "none"
        pending = ", ".join(self.pending_symbols) or "none"
        raise ExtractionBatchError(
            f"Endpoint '{self.endpoint}' did not complete its batch. Failed: {failed}. Pending: {pending}."
        )
