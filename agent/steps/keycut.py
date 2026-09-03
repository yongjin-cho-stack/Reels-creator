"""단계 A · 키컷 생성 — 레퍼런스로 인물 기준을 만든다.

자료(영상독학)는 키컷을 미드저니로 손수 만들라고 한다. 품질 때문이다.
그런데 미드저니는 API 가 없어서 **자동화 대상에서 빠진다.**
단계는 곧 에이전트가 될 자리이므로, fal 나노바나나 프로(참조 최대 14장)로 간다.

★ 이 단계의 알맹이는 «레퍼런스마다 역할을 지정하는 것»이다.
  그림을 여러 장 넣고 역할을 말로 안 정하면 전부 섞여서 이상하게 나온다.
"""

from __future__ import annotations

from ..paths import KEYCUT, KEYCUTS, REFS, STYLE, rel
from ..providers import fal
from ._common import load_keycut, require_dir, save_json

MODEL = "fal-ai/nano-banana-pro/edit"
PRICE_PER_IMAGE = 0.15          # 모델 페이지 실측: "$0.15 per image" (1K·2K)
NUM_IMAGES = 2                  # 후보 수

# 참조 그림과 그 «역할». 역할을 안 적으면 섞인다.
REFERENCE_ROLES = [
    ("style/모델.jpg", "자세와 이목구비 구조"),
    ("cut03.jpg", "얼굴 각도 · 안경 · 몰입한 표정"),
    ("cut04_win1.jpg", "조명 · 작업실 분위기 · 터틀넥 질감"),
]

# 이 문장이 없으면 참조 인물이 그대로 나온다.
# 자료: "외국인 남자분의 얼굴이 이런 느낌으로 바뀐 거죠"
NO_COPY = (
    "※ 첫 번째 참조 인물의 얼굴을 그대로 복제하지 말 것. "
    "자세와 조명만 가져오고 얼굴은 새로 세울 것."
)


def build_prompt(card: dict) -> str:
    k = card
    parts = [
        k["face"],
        k["outfit"],
        "캔버스 앞에서 붓을 들고 그림을 응시하는 자세",
        k["time_of_day"],
        NO_COPY,
    ]
    return "\n".join(p for p in parts if p)


def check() -> dict:
    """입력이 갖춰졌는지 본다. 갖춰졌으면 계획을 돌려준다."""
    kc = load_keycut()
    require_dir(STYLE, "기획이 refs/style/ 에 질감·인물 레퍼런스를 넣어야 합니다.")

    card = kc["keycuts"][0]
    refs, missing = [], []
    for name, role in REFERENCE_ROLES:
        p = REFS / name
        (refs if p.exists() else missing).append((p, role))

    return {
        "keycut_id": card["id"],
        "approved": card.get("approved", False),
        "prompt": build_prompt(card),
        "refs": refs,
        "missing": missing,
        "planned_usd": PRICE_PER_IMAGE * NUM_IMAGES,
    }


def run(dry: bool = True, only: int | None = None) -> None:
    plan = check()
    KEYCUTS.mkdir(exist_ok=True)

    print(f"[A 키컷] {MODEL}")
    print(f"  대상      {plan['keycut_id']}  (approved={plan['approved']})")
    print(f"  fal 열쇠  {fal.key_status()}")
    print(f"  참조 그림 {len(plan['refs'])}장")
    for p, role in plan["refs"]:
        print(f"    · {rel(p):<28} → {role}")
    for p, role in plan["missing"]:
        print(f"    ✗ {rel(p):<28} → {role}  (없음)")
    print(f"  후보      {NUM_IMAGES}장 · 2K · 16:9")
    print(f"  예상 비용 ${plan['planned_usd']:.2f}")
    print("  주문서")
    for line in plan["prompt"].splitlines():
        print(f"    | {line}")

    if dry:
        print("  → 시험 실행(--dry). 실제 호출 안 함.")
        return
    if not plan["refs"]:
        print("  ⏸ 참조 그림이 하나도 없습니다.")
        return

    print("  참조를 올리는 중…")
    urls = [fal.upload(p) for p, _ in plan["refs"]]

    print(f"  생성 중…  (몇십 초 걸립니다)")
    out = fal.generate(plan["prompt"], urls, num_images=NUM_IMAGES,
                       resolution="2K", aspect_ratio="16:9",
                       step="keycut", target=plan["keycut_id"])

    saved = []
    for i, u in enumerate(out):
        dst = KEYCUTS / f"{plan['keycut_id']}_{chr(ord('a') + i)}.png"
        fal.download(u, dst)
        saved.append(dst)
        print(f"  ✅ {rel(dst)}")

    print()
    print("  → 하나를 골라 keycut.json 에 적으세요:")
    print(f'       "approved_image": "keycuts/{saved[0].name}",  "approved": true')
    print("     그래야 D(컷 이미지)가 시작됩니다.")
