from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BenchmarkResult:
    name: str
    suite: str
    elapsed: float
    unit: str = "s"
    extra: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    threshold: Optional[float] = None
    skipped: bool = False

    @property
    def passed(self) -> bool:
        if self.skipped:
            return True
        if self.error:
            return False
        if self.threshold is not None:
            return self.elapsed <= self.threshold
        return True

    @property
    def status(self) -> str:
        if self.skipped:
            return "SKIP"
        if self.error:
            return "ERROR"
        if self.threshold is not None:
            return "PASS" if self.elapsed <= self.threshold else "FAIL"
        return "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "suite": self.suite,
            "elapsed": round(self.elapsed, 4),
            "unit": self.unit,
            "status": self.status,
            "threshold": self.threshold,
            "extra": self.extra,
            "error": self.error,
            "skipped": self.skipped,
        }
