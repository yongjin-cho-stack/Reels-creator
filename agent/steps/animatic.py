"""단계 B · 애니매틱 — 정지 이미지 + 음악으로 «움직이지 않는 16.41초».

**돈이 제일 많이 나가는 영상화 바로 앞에 있다.**
여기서 길이·흐름의 잘못을 잡으면 공짜로 잡고, 못 잡으면 클링 값을 다 치르고 나서 잡는다.
자료가 "1분 30초로 만들려는데 넘어가는 경우가 많다"고 한 사고를 막는 자리다.

이미지가 아직 없으면 **원본 구도 프레임(refs/)** 을 그 자리에 놓고 만든다.
그러면 아무도 안 기다리고 이 단계를 끝까지 완성할 수 있다.
"""

from __future__ import annotations

from ..paths import ANIMATIC, BGM, IMAGES, ROOT, rel
from ._common import load_cuts, overlays, timeline, total_seconds

FPS = 30
SIZE = (1920, 1080)


def source_for(cut: dict) -> tuple:
    """이 컷에 쓸 정지 이미지. 생성본이 있으면 그것, 없으면 원본 구도 프레임."""
    made = IMAGES / f"cut{cut['id']:02d}.png"
    if made.exists():
        return made, "생성"
    return ROOT / cut["ref_frame"], "원본(대체)"


def check() -> dict:
    cuts = load_cuts()
    base = timeline(cuts)
    over = overlays(cuts)

    tracks, missing = [], []
    for cut in cuts["cuts"]:
        src, kind = source_for(cut)
        (tracks if src.exists() else missing).append((cut, src, kind))

    bgm = sorted(BGM.glob("*")) if BGM.is_dir() else []

    return {
        "base": base,
        "overlays": over,
        "tracks": tracks,
        "missing": missing,
        "bgm": bgm,
        "seconds": total_seconds(cuts),
    }


def run(dry: bool = True) -> None:
    plan = check()

    print("[B 애니매틱]  kitkat")
    print(f"  길이      {plan['seconds']}초 · {SIZE[0]}×{SIZE[1]} · {FPS}fps")
    print(f"  바닥 트랙 {len(plan['base'])}컷")
    for c in plan["base"]:
        src, kind = source_for(c)
        mark = " " if src.exists() else "✗"
        print(f"    {mark} 컷{c['id']:>2}  {c['start_s']:>6.2f}–{c['end_s']:<6.2f} "
              f"({c['end_s'] - c['start_s']:.2f}s)  {kind:<9} {rel(src)}")
    if plan["overlays"]:
        print(f"  오버레이  {len(plan['overlays'])}컷 (분할화면)")
        for c in plan["overlays"]:
            print(f"      컷{c['id']:>2}  {c['start_s']:>6.2f}부터  {c['shot_type']}")
    print(f"  음악      {len(plan['bgm'])}개" + (f"  {plan['bgm'][0].name}" if plan["bgm"] else "  (없음 — 원본 오디오로 대체 가능)"))
    print(f"  결과      {rel(ANIMATIC)}")

    if dry:
        print("  → 시험 실행(--dry). kitkat 호출 안 함.")
        return

    raise NotImplementedError("kitkat 배선은 다음 차례입니다 (providers/kitkat.py)")
