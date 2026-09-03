"""단계 · 영상화(제작A) — 컷 이미지 → 클링 영상.

D(컷 이미지)가 사람이 고른 `images/cutNN.png`를 채택본으로 남기고 나면,
그 이미지 한 장을 클링에 넣어 짧은 영상으로 만드는 자리다.

  D 이미지 : 컷 이미지 후보 여러 장 → 사람이 1장 골라 images/cutNN.png
  이 단계 : 그 1장 → 클링 영상 후보 여러 개 → 사람이 원본과 제일 비슷한 걸 선택

**승인 게이트 ② «베스트컷 선택»이 여기서 일어난다.**

클링은 임의의 길이를 못 받고 5초/10초만 받는다(providers/fal.generate_video 참고).
그래서 컷이 그보다 짧아도 항상 5초로 뽑고, 필요한 만큼만 편집(C-1)에서 앞을 잘라 쓴다
— edit.py 의 `in`/`out`(trims)이 이미 그 트리밍을 하도록 짜여 있다.

나노바나나(이미지)와 달리 클링은 한 번 호출에 영상 1개만 나온다.
그래서 컷당 후보 3개 = API 호출 3번이다 — image.py 처럼 한 번에 여러 장이 아니다.
"""

from __future__ import annotations

from ..paths import IMAGES, ROOT, VIDEOS, rel
from ..providers import fal
from ._common import load_cuts

DURATION_S = 5                  # 클링 고정 길이. 편집 단계에서 필요한 만큼만 잘라 씀
NUM_CANDIDATES = 3               # 컷당 후보 수 — 제작A 산출물 규약(README)과 맞춤

# 정적인 결과를 막는 문구 — reel-pipeline 에서도 같은 이유로 넣었던 것과 같다.
NO_STATIC = "자연스럽게 움직일 것 — 정지된 사진처럼 가만히 있지 말 것."


def build_prompt(cut: dict) -> str:
    return "\n".join([
        f"행동: {cut['action']}",
        f"카메라: {cut['camera_move']}",
        "※ 인물의 얼굴·의상·소품을 유지할 것.",
        NO_STATIC,
    ])


def image_for(cut: dict):
    """이 컷의 채택된 이미지.

    「후보 중 무엇을 골랐나」를 적는 방법이 두 가지다. 둘 다 받는다.

      ① cuts.json 의 `selected_image` 에 적는다   ← 스키마 v3, 이쪽을 권한다
      ② images/cutNN.png 로 이름을 바꾼다          ← 예전 방식, 그대로 산다

    ①을 권하는 이유: 이름을 바꾸면 후보가 둘이었다는 기록이 사라져서
    나중에 「b 가 나았나」를 다시 못 본다. 그리고 11컷이면 손으로 11번,
    30초 광고면 22번 바꿔야 해서 사람이 틀린다.
    """
    sel = cut.get("selected_image")
    if sel:
        p = ROOT / sel
        if p.exists():
            return p
    for ext in ("png", "jpg"):
        p = IMAGES / f"cut{cut['id']:02d}.{ext}"
        if p.exists():
            return p
    return None


def check() -> dict:
    cuts = load_cuts()
    jobs, missing = [], []
    for cut in cuts["cuts"]:
        img = image_for(cut)
        (jobs if img else missing).append((cut, img))
    return {
        "jobs": jobs,
        "missing": missing,
        "planned_usd": fal.video_price(DURATION_S) * NUM_CANDIDATES * len(jobs),
    }


def run(dry: bool = True, only: int | None = None) -> None:
    plan = check()
    VIDEOS.mkdir(exist_ok=True)
    jobs = [j for j in plan["jobs"] if only is None or j[0]["id"] == only]
    usd = fal.video_price(DURATION_S) * NUM_CANDIDATES * len(jobs)

    print(f"[제작A 영상화] {fal.MODEL_VIDEO}")
    print(f"  fal 열쇠  {fal.key_status()}")
    print(f"  컷 {len(jobs)}개 × {NUM_CANDIDATES}개 = {len(jobs) * NUM_CANDIDATES}개"
          + (f"   (컷 {only} 만)" if only else ""))
    print(f"  길이      {DURATION_S}초 고정 (편집 단계에서 필요한 만큼 잘라 씀)")
    print(f"  예상 비용 ${usd:.2f}")
    for cut, img in jobs[:4]:
        print(f"    · 컷{cut['id']:>2}  {rel(img)}  ← {cut['action'][:30]}")
    if len(jobs) > 4:
        print(f"    · … 외 {len(jobs) - 4}개")
    for cut, _ in plan["missing"]:
        print(f"    ✗ 컷{cut['id']:>2}  images/cut{cut['id']:02d}.png 없음 (D 단계 먼저)")

    if dry:
        print("  → 시험 실행(--dry). 실제 호출 안 함.")
        return
    if not jobs:
        print("  ⏸ 만들 컷이 없습니다.")
        return

    for cut, img in jobs:
        print(f"  컷{cut['id']:>2} 생성 중… (후보 {NUM_CANDIDATES}개, 몇 분 걸릴 수 있음)")
        img_url = fal.upload(img)
        for i in range(NUM_CANDIDATES):
            url = fal.generate_video(
                build_prompt(cut), img_url, duration_s=DURATION_S,
                step="video", target=f"cut{cut['id']:02d}")
            dst = VIDEOS / f"cut{cut['id']:02d}_{chr(ord('a') + i)}.mp4"
            fal.download(url, dst)
            print(f"    ✅ {rel(dst)}")

    print()
    print("  → 컷마다 원본과 제일 비슷한 걸 골라 videos/cutNN.mp4 로 이름을 바꾸세요.")
    print("     그래야 C(편집)가 시작됩니다.")
