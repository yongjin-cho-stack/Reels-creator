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

**안 됐던 것 둘 — 둘 다 프롬프트 문제였고, 스키마로 고쳤다(아직 재검증 전).**

① **구도 지시가 약했다.**
   원본 컷 3은 «얼굴이 화면 절반을 채우는 클로즈업»인데 생성본은 인물이 작고
   공간이 많았다. `shot_type: "클로즈업"` 만으로는 **인물 크기가 안 잡힌다** —
   구도 참조 이미지를 넣었는데도 그랬다.
   → cuts.json 에 `framing` 을 넣었다. 「얼굴이 프레임 높이의 60~70%」처럼
     **숫자로** 적는 칸이다.

② **props 가 매 컷에 전부 나왔다.**
   keycut.json 의 props 를 통째로 주문서에 넣었더니 컷 3(붓질하는 장면)에
   **찻잔·자사호·옹기·일로향이 다 깔렸다.**
   → cuts.json 에 컷별 `props` 를 넣었다. keycut 의 props 는 «이 인물이 쓰는
     물건 전부»고, cuts 의 props 는 «이 컷에 실제로 보이는 것»이다.

**둘 다 컷 3 을 다시 뽑아 봐야 확인된다($0.30).**
"""

from __future__ import annotations


from ..paths import IMAGES, ROOT, rel
from ..providers import fal
from ._common import StepBlocked, load_cuts, load_keycut

MODEL = "fal-ai/nano-banana-pro/edit"
PRICE_PER_IMAGE = 0.15
NUM_IMAGES = 2                  # 컷당 후보 수


# shot_type 은 촬영 용어라 모델이 «크기»로 못 읽는다. 크기 문장으로 번역한다.
# cuts.json 의 framing 이 있으면 그게 이깁니다 — 사전은 기본값일 뿐이다.
FRAMING = {
    "익스트림 클로즈업": "대상이 프레임을 거의 가득 채운다. 배경은 조금만 흐릿하게",
    "클로즈업": "얼굴이 프레임 높이의 60~70%. 어깨 위만 보인다",
    "미디엄샷": "허리 위가 보인다. 인물이 프레임 높이의 절반쯤",
    "풀샷": "전신과 공간이 함께 보인다. 인물은 프레임 높이의 1/3 이하",
    "항공샷": "위에서 수직으로 내려다본다",
}


def build_prompt(card: dict, cut: dict) -> str:
    """키컷 카드(인물) + 그 컷의 화면·행동·소품.

    ## 2026-09-03 에 고친 두 가지

    ① **소품은 이 컷에 나오는 것만.** 예전엔 keycut.json 의 props 를 통째로
       넣어서, 붓질하는 컷에 찻잔·자사호·옹기·일로향이 다 깔렸다.
       이제 cuts.json 의 `props` 를 쓴다 — 무엇이 나오는지는 기획이 정할 일이다.

    ② **구도를 크기 문장으로.** shot_type «클로즈업» 만으로는 인물 크기가 안
       잡혀서 원본보다 인물이 작게 나왔다. framing 을 같이 준다.
    """
    frame = cut.get("framing") or FRAMING.get(cut["shot_type"], cut["shot_type"])
    props = cut.get("props")
    if props is None:                      # 스키마 v1 대비 — 없으면 옛 방식
        props = card.get("props", [])

    lines = [
        f"{card['face']} · {card['outfit']}",
        f"장소·시간: {card['time_of_day']}",
        f"행동: {cut['action']}",
        f"화면: {frame} · 카메라 {cut['camera_move']}",
    ]
    if props:
        lines.append(f"이 컷에 보이는 것: {', '.join(props)}")
        lines.append("※ 위에 적지 않은 소품은 화면에 두지 말 것.")
    if cut.get("fantasy"):
        lines.append(f"연출: {cut['fantasy']}")
    lines += [
        "※ 첫 번째 참조(키컷)의 얼굴·머리·의상을 그대로 유지할 것.",
        "※ 두 번째 참조는 **화면 배치와 인물이 차지하는 크기·위치**를 그대로 따를 것. "
        "인물 자체는 첫 번째 참조를 따른다.",
    ]
    return chr(10).join(lines)


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


def run(dry: bool = True, only: int | None = None, num: int | None = None) -> None:
    plan = check()
    IMAGES.mkdir(exist_ok=True)
    n = num or NUM_IMAGES
    jobs = [j for j in plan["jobs"] if only is None or j[0]["id"] == only]
    usd = PRICE_PER_IMAGE * n * len(jobs)

    print(f"[D 컷 이미지] {MODEL}")
    print(f"  키컷      {plan['card'].get('approved_image')}")
    print(f"  컷 {len(jobs)}개 × {n}장 = {len(jobs) * n}장"
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
            num_images=n, resolution="2K", aspect_ratio="16:9",
            step="image", target=f"cut{cut['id']:02d}")
        for i, u in enumerate(urls):
            dst = IMAGES / f"cut{cut['id']:02d}_{chr(ord('a') + i)}.png"
            fal.download(u, dst)
            print(f"    ✅ {rel(dst)}")
    print("  → 컷마다 한 장을 골라 cuts.json 의 selected_image 에 적으세요.")
    print('     예: "selected_image": "images/cut03_a.png"')
