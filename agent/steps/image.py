"""단계 D · 컷 이미지 생성 — 키컷 + 구도 참고 → 컷별 시작 이미지.

키컷과 같은 모델이고 주문서 조립만 다르다. 넣는 그림이 바뀔 뿐이다.

  A 키컷   : 모델 + 분위기 + 조명   → 인물 기준
  D 이미지 : **채택된 키컷** + 컷별 원본 프레임 → 컷 이미지

스타일 레퍼런스는 여기 넣지 않는다. 이미 키컷에 녹아 있어서
또 넣으면 서로 상쇄돼 흐려진다.
"""

from __future__ import annotations

from ..paths import IMAGES, KEYCUT, ROOT, rel
from ._common import StepBlocked, load_cuts, load_keycut
from .. import cost

MODEL = "fal-ai/nano-banana-pro/edit"
PRICE_PER_IMAGE = 0.15
NUM_IMAGES = 2                  # 컷당 후보 수


def build_prompt(card: dict, cut: dict) -> str:
    """키컷 카드 전문 + 그 컷의 행동·샷."""
    return "\n".join([
        f"{card['face']} · {card['outfit']}",
        f"소품: {', '.join(card['props'])}",
        card["time_of_day"],
        f"행동: {cut['action']}",
        f"샷: {cut['shot_type']} · 카메라 {cut['camera_move']}",
        "※ 첫 번째 참조 인물(키컷)의 얼굴·의상·소품을 그대로 유지할 것.",
        "※ 두 번째 참조는 구도만 가져오고 인물은 키컷을 따를 것.",
    ])


def check() -> dict:
    cuts = load_cuts()
    kc = load_keycut()
    card = kc["keycuts"][0]

    if not card.get("approved"):
        raise StepBlocked(
            "키컷이 아직 승인되지 않았습니다 (keycut.json · approved=false).\n"
            "  → 단계 A 를 돌려 후보를 뽑고, 하나를 골라 approved_image 와 "
            "approved=true 를 적으세요."
        )

    jobs, missing = [], []
    for cut in cuts["cuts"]:
        ref = ROOT / cut["ref_frame"]
        (jobs if ref.exists() else missing).append((cut, ref))

    return {
        "card": card,
        "jobs": jobs,
        "missing": missing,
        "planned_usd": PRICE_PER_IMAGE * NUM_IMAGES * len(jobs),
    }


def run(dry: bool = True) -> None:
    plan = check()
    IMAGES.mkdir(exist_ok=True)

    print(f"[D 컷 이미지] {MODEL}")
    print(f"  컷 {len(plan['jobs'])}개 × {NUM_IMAGES}장 = {len(plan['jobs']) * NUM_IMAGES}장")
    print(f"  예상 비용 ${plan['planned_usd']:.2f}")
    for cut, ref in plan["jobs"][:3]:
        print(f"    · 컷{cut['id']:>2}  구도 {rel(ref)}  ← {cut['shot_type']}")
    if len(plan["jobs"]) > 3:
        print(f"    · … 외 {len(plan['jobs']) - 3}개")
    for cut, ref in plan["missing"]:
        print(f"    ✗ 컷{cut['id']:>2}  {rel(ref)} 없음")

    if dry:
        print("  → 시험 실행(--dry). 실제 호출 안 함.")
        return

    cost.guard(plan["planned_usd"])
    raise NotImplementedError("fal 배선은 다음 차례입니다 (providers/fal.py)")
