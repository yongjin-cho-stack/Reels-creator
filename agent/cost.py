"""비용 기록 — 돈을 쓰기 전에 이것부터 만든다.

나중에 붙이면 초반 지출 기록이 통째로 없다. 그래서 제일 먼저 만든다.
돈을 쓰는 모든 호출은 예외 없이 여기를 거친다.
"""

from __future__ import annotations

import os
from datetime import datetime

from .paths import COST_LOG

# 한 번 실행에 이 금액을 넘으면 멈추고 사람에게 묻는다.
# 오타 하나로 22장이 220장이 되는 사고를 막는 자리다.
DEFAULT_LIMIT_USD = float(os.getenv("AGENT_COST_LIMIT_USD", "5.0"))


class CostLimitExceeded(RuntimeError):
    pass


def log(step: str, model: str, target: str, count: int, usd: float) -> None:
    """호출 한 건을 한 줄로 남긴다."""
    line = (
        f"{datetime.now().isoformat(timespec='seconds')}\t"
        f"{step}\t{model}\t{target}\t{count}개\t${usd:.4f}\n"
    )
    with COST_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def total() -> float:
    """지금까지 쓴 돈 전부."""
    if not COST_LOG.exists():
        return 0.0
    s = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 6 and parts[5].startswith("$"):
            try:
                s += float(parts[5][1:])
            except ValueError:
                pass
    return s


def guard(planned_usd: float, limit: float | None = None) -> None:
    """쓰기 전에 부른다. 상한을 넘으면 멈춘다."""
    lim = DEFAULT_LIMIT_USD if limit is None else limit
    if planned_usd > lim:
        raise CostLimitExceeded(
            f"이번 실행 예상 ${planned_usd:.2f} 가 상한 ${lim:.2f} 를 넘습니다.\n"
            f"정말 쓰려면 AGENT_COST_LIMIT_USD 를 올리세요."
        )
