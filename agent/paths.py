"""경로 규약 — 파일 이름을 한곳에 모은다.

단계끼리는 직접 말을 주고받지 않고 **파일로만** 이어진다.
그래서 이름이 흩어지면 곧 어긋난다. 여기가 그 단일 출처다.
"""

from __future__ import annotations

from pathlib import Path

# 이 파일 기준 두 단계 위가 레포 루트 (agent/paths.py → agent/ → 루트)
ROOT = Path(__file__).resolve().parent.parent

# ── 기획 산출물 (사람이 만들어 넣는다) ──────────────────────────────
CUTS = ROOT / "cuts.json"
KEYCUT = ROOT / "keycut.json"
REFS = ROOT / "refs"
STYLE = REFS / "style"

# ── 단계 산출물 ────────────────────────────────────────────────────
KEYCUTS = ROOT / "keycuts"          # A · 키컷 후보와 채택본
IMAGES = ROOT / "images"            # 컷별 시작 이미지 (담당 미정)
VIDEOS = ROOT / "videos"            # 제작A · 클링 결과
BGM = ROOT / "bgm"                  # 제작B · 음악
ANIMATIC = ROOT / "animatic.mp4"    # B
FINAL = ROOT / "final.mp4"          # C

# ── 기록 ───────────────────────────────────────────────────────────
COST_LOG = ROOT / "cost.log"

# ── 개발용 대체재 ──────────────────────────────────────────────────
# 제작A의 영상이 아직 없을 때, 원본을 컷별로 자른 조각을 그 자리에 놓는다.
# 이러면 제작B가 아무도 안 기다리고 10단계를 끝까지 만들 수 있다.
FAKE_VIDEOS = ROOT / "videos_fake"


def rel(p: Path) -> str:
    """레포 루트 기준 상대경로 — 화면에 찍을 때 쓴다."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)
