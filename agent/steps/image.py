"""단계 D · 컷 이미지 생성 — 키컷 + 구도 참고 → 컷별 시작 이미지.

키컷과 같은 모델이고 주문서 조립만 다르다. 넣는 그림이 바뀔 뿐이다.

  A 키컷   : 모델 + 분위기 + 조명   → 인물 기준
  D 이미지 : **채택된 키컷** + 컷별 원본 프레임 → 컷 이미지

스타일 레퍼런스는 여기 넣지 않는다. 이미 키컷에 녹아 있어서
또 넣으면 서로 상쇄돼 흐려진다.

## 2026-09-03 · 컷 3 하나를 $0.30 에 뽑아 보고 알아낸 것

**된 것 — 인물이 안 섞인다.**
키컷(여성)과 원본 프레임(남성)을 같이 넣었는데 **원본 남자 얼굴이 안 들어왔다.**
참조마다 역할을 지정하는 방식이 A·D 두 단계 연속으로 작동했다.

**아직 안 된 것 둘. 둘 다 프롬프트 문제다.**

① **구도 지시가 약하다.**
   원본 컷 3은 «얼굴이 화면 절반을 채우는 클로즈업»인데 생성본은 인물이 작고
   공간이 많다. `shot_type: "클로즈업"` 만으로는 **인물 크기가 안 잡힌다** —
   구도 참조 이미지를 넣었는데도 그렇다.
   → 「얼굴이 프레임 높이의 60% 이상」처럼 **숫자로** 적어야 한다.
     cuts.json 에 그 칸이 없다(framing 같은 것). 팀과 정할 일이다.

② **props 가 매 컷에 전부 나온다.**
   keycut.json 의 props 를 통째로 주문서에 넣었더니 컷 3(붓질하는 장면)에
   **찻잔·자사호·옹기·일로향이 다 깔렸다.**
   → props 를 갈라야 한다:
       고정 소품   붓 · 팔레트 · 안경      — 인물에 늘 붙어 있는 것
       컷별 소품   다구 · 제품 · 옹기      — 그 컷에만 나오는 것
     지금은 build_prompt 가 props 전부를 넣는다. 여기가 고칠 자리다.
"""

from __future__ import annotations

from ..paths import IMAGES, ROOT, rel
from ..providers import fal
from ._common import StepBlocked, load_cuts, load_keycut

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


def run(dry: bool = True, only: int | None = None) -> None:
    plan = check()
    IMAGES.mkdir(exist_ok=True)
    jobs = [j for j in plan["jobs"] if only is None or j[0]["id"] == only]
    usd = PRICE_PER_IMAGE * NUM_IMAGES * len(jobs)

    print(f"[D 컷 이미지] {MODEL}")
    print(f"  키컷      {plan['card'].get('approved_image')}")
    print(f"  컷 {len(jobs)}개 × {NUM_IMAGES}장 = {len(jobs) * NUM_IMAGES}장"
          + (f"   (컷 {only} 만)" if only else ""))
    print(f"  예상 비용 ${usd:.2f}")
    for cut, ref in jobs[:4]:
        print(f"    · 컷{cut['id']:>2}  구도 {rel(ref)}  ← {cut['shot_type']}")
    if len(jobs) > 4:
        print(f"    · … 외 {len(jobs) - 4}개")
    for cut, ref in plan["missing"]:
        print(f"    ✗ 컷{cut['id']:>2}  {rel(ref)} 없음")

    if dry:
        print("  → 시험 실행(--dry). 실제 호출 안 함.")
        return
    if not jobs:
        print("  ⏸ 만들 컷이 없습니다.")
        return

    key_url = fal.upload(ROOT / plan["card"]["approved_image"])
    for cut, ref in jobs:
        print(f"  컷{cut['id']:>2} 생성 중…")
        urls = fal.generate(
            build_prompt(plan["card"], cut),
            [key_url, fal.upload(ref)],          # ① 이 인물  ② 이 구도
            num_images=NUM_IMAGES, resolution="2K", aspect_ratio="16:9",
            step="image", target=f"cut{cut['id']:02d}")
        for i, u in enumerate(urls):
            dst = IMAGES / f"cut{cut['id']:02d}_{chr(ord('a') + i)}.png"
            fal.download(u, dst)
            print(f"    ✅ {rel(dst)}")
    print("  → 컷마다 한 장을 골라 images/cutNN.png 로 이름을 바꾸세요.")
