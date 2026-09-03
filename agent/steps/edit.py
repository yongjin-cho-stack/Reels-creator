"""단계 C · 최종 편집 — 영상 조각을 조립해 final.mp4.

B(애니매틱)의 뼈대를 거의 그대로 쓴다. 차이는 «정지 이미지냐 영상이냐» 뿐이다.
그래서 B 를 먼저 만들면 C 는 거의 따라온다.

이 단계에만 있는 특수 작업이 하나 있다 — **컷 4의 분할화면**.
배경 항공샷 위에 창 3개가 시각차를 두고 열린다. 생성이 아니라 편집이다.
"""

from __future__ import annotations

from ..paths import BGM, FAKE_VIDEOS, FINAL, VIDEOS, rel
from ._common import load_cuts, overlays, timeline, total_seconds

# 분할화면 창의 자리 — 원본 1920×1080 프레임에서 잰 값.
# (x, y, w, h) 왼쪽 위 기준
WINDOW_BOX = {
    5: (180, 80, 850, 485),      # 창1 붓질하는 측면
    6: (1030, 222, 825, 618),    # 창2 팔레트에 물감 붓기
    7: (280, 565, 650, 350),     # 창3 붓으로 물감 섞기
}


def source_for(cut: dict) -> tuple:
    """이 컷에 쓸 영상. 제작A 결과가 있으면 그것, 없으면 원본 조각(개발용)."""
    for d, kind in ((VIDEOS, "제작A"), (FAKE_VIDEOS, "원본조각")):
        if d.is_dir():
            hit = sorted(d.glob(f"cut{cut['id']:02d}*"))
            if hit:
                return hit[0], kind
    return VIDEOS / f"cut{cut['id']:02d}.mp4", "없음"


def check() -> dict:
    cuts = load_cuts()
    ready, missing = [], []
    for cut in cuts["cuts"]:
        src, kind = source_for(cut)
        (ready if src.exists() else missing).append((cut, src, kind))

    return {
        "base": timeline(cuts),
        "overlays": overlays(cuts),
        "ready": ready,
        "missing": missing,
        "bgm": sorted(BGM.glob("*")) if BGM.is_dir() else [],
        "seconds": total_seconds(cuts),
    }


def run(dry: bool = True) -> None:
    plan = check()

    print("[C 최종 편집]  kitkat")
    print(f"  길이      {plan['seconds']}초")
    print(f"  준비된 컷 {len(plan['ready'])} / {len(plan['ready']) + len(plan['missing'])}")
    for cut, src, kind in plan["ready"][:4]:
        print(f"    · 컷{cut['id']:>2}  {kind:<8} {rel(src)}")
    if len(plan["ready"]) > 4:
        print(f"    · … 외 {len(plan['ready']) - 4}개")
    for cut, src, kind in plan["missing"]:
        print(f"    ✗ 컷{cut['id']:>2}  영상 없음")

    if plan["overlays"]:
        print("  분할화면 (컷 4 위에 얹는다)")
        for c in plan["overlays"]:
            box = WINDOW_BOX.get(c["id"])
            pos = f"{box[0]},{box[1]} {box[2]}×{box[3]}" if box else "자리 미정"
            print(f"      컷{c['id']:>2}  {c['start_s']:>6.2f}s 등장  {pos}")

    print(f"  결과      {rel(FINAL)}")

    if dry:
        print("  → 시험 실행(--dry). kitkat 호출 안 함.")
        return

    raise NotImplementedError("kitkat 배선은 다음 차례입니다 (providers/kitkat.py)")
