"""단계 공통 규약.

열 단계가 전부 이걸 지킨다.

  - 앞 단계 파일을 읽는다. 없으면 **무엇이 없는지** 말하고 멈춘다
  - 자기 산출물을 정해진 이름으로 쓴다
  - 돈을 쓰면 cost.log 에 남긴다
  - 여러 개 뽑는 단계는 전부 남기고, 사람이 고른 건 파일에 적는다
  - 혼자 다시 돌릴 수 있다 — 앞 단계를 다시 안 돌려도 된다
"""

from __future__ import annotations

import json
from pathlib import Path

from ..paths import CUTS, KEYCUT, rel


class StepBlocked(RuntimeError):
    """앞 단계가 안 끝나서 진행할 수 없다. 무엇을 먼저 해야 하는지 담는다."""


def require(path: Path, hint: str) -> Path:
    """없으면 «무엇이 없고 무엇을 먼저 해야 하는지» 말하고 멈춘다."""
    if not path.exists():
        raise StepBlocked(f"{rel(path)} 가 없습니다.\n  → {hint}")
    return path


def require_dir(path: Path, hint: str, at_least: int = 1) -> Path:
    if not path.is_dir():
        raise StepBlocked(f"{rel(path)}/ 가 없습니다.\n  → {hint}")
    n = sum(1 for p in path.iterdir() if p.is_file())
    if n < at_least:
        raise StepBlocked(f"{rel(path)}/ 에 파일이 {n}개뿐입니다(최소 {at_least}).\n  → {hint}")
    return path


def load_cuts() -> dict:
    require(CUTS, "기획이 cuts.json 을 채워야 합니다.")
    return json.loads(CUTS.read_text(encoding="utf-8"))


def load_keycut() -> dict:
    require(KEYCUT, "기획이 keycut.json 을 채워야 합니다.")
    return json.loads(KEYCUT.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def timeline(cuts: dict) -> list[dict]:
    """바닥 트랙(layer 0) 컷만 시각 순으로.

    스키마 v2 부터 `layer` 가 이걸 **명시**한다 — 0 은 바닥, 1 이상은 그 위에
    얹히는 창이다. v1 때는 «시간이 겹치면 오버레이»로 추론했는데, 실수로 겹친
    컷과 일부러 겹친 컷을 구분 못 해서 위험했다. 없으면 옛 방식으로 떨어진다.
    """
    items = sorted(cuts["cuts"], key=lambda c: (c["start_s"], c["id"]))
    if any("layer" in c for c in items):
        return [c for c in items if c.get("layer", 0) == 0]
    out: list[dict] = []
    for c in items:
        if out and c["start_s"] < out[-1]["end_s"] - 1e-6:
            continue
        out.append(c)
    return out


def overlays(cuts: dict) -> list[dict]:
    """바닥 위에 얹히는 컷들 (분할화면 창). layer 순으로 아래→위."""
    base_ids = {c["id"] for c in timeline(cuts)}
    ov = [c for c in cuts["cuts"] if c["id"] not in base_ids]
    return sorted(ov, key=lambda c: (c.get("layer", 1), c["start_s"]))


def total_seconds(cuts: dict) -> float:
    base = timeline(cuts)
    return round(base[-1]["end_s"] - base[0]["start_s"], 3) if base else 0.0
