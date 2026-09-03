"""단계 B · 애니매틱 — 정지 이미지 + 음악으로 «움직이지 않는 16.41초».

**돈이 제일 많이 나가는 영상화 바로 앞에 있다.**
여기서 길이·흐름의 잘못을 잡으면 공짜로 잡고, 못 잡으면 클링 값을 다 치르고 나서 잡는다.
자료가 "1분 30초로 만들려는데 넘어가는 경우가 많다"고 한 사고를 막는 자리다.

이미지가 아직 없으면 **원본 구도 프레임(refs/)** 을 그 자리에 놓고 만든다.
그러면 아무도 안 기다리고 이 단계를 끝까지 완성할 수 있다.

C(최종 편집)가 이 코드를 거의 그대로 쓴다 — 정지 이미지 자리에 영상이 들어갈 뿐이다.
"""

from __future__ import annotations

import shutil

from ..paths import ANIMATIC, BGM, IMAGES, ROOT, rel
from ..providers import kitkat
from ._common import load_cuts, overlays, timeline, total_seconds

FPS = 30
W, H = 1920, 1080


def source_for(cut: dict) -> tuple:
    """이 컷에 쓸 정지 이미지. 생성본이 있으면 그것, 없으면 원본 구도 프레임."""
    for ext in ("png", "jpg"):
        made = IMAGES / f"cut{cut['id']:02d}.{ext}"
        if made.exists():
            return made, "생성"
    return ROOT / cut["ref_frame"], "원본(대체)"


def pick_bgm():
    if not BGM.is_dir():
        return None
    for p in sorted(BGM.iterdir()):
        if p.is_file() and p.suffix.lower() in (".wav", ".mp3", ".m4a", ".aac"):
            return p
    return None


def check() -> dict:
    cuts = load_cuts()
    base = timeline(cuts)
    tracks, missing = [], []
    for cut in cuts["cuts"]:
        src, kind = source_for(cut)
        (tracks if src.exists() else missing).append((cut, src, kind))
    return {
        "cuts": cuts, "base": base, "overlays": overlays(cuts),
        "tracks": tracks, "missing": missing,
        "bgm": pick_bgm(), "seconds": total_seconds(cuts),
    }


def build(plan: dict) -> tuple[str, str]:
    """kitkat 에 타임라인을 세우고 (프로젝트 id, 편집기 주소) 를 돌려준다.

    C 단계가 이 함수를 그대로 부른다 — `kind` 만 image ↔ video 로 바뀐다.
    """
    doc = kitkat.create_project("오설록 17초 · 애니매틱")
    pid = doc["id"]
    vt = kitkat.track_of(doc, "video")
    at = kitkat.track_of(doc, "audio")

    # 기본이 1080×1920 세로다. 가로로 돌린다.
    cmds = [kitkat.cmd_settings(W, H, FPS)]

    for cut in plan["base"]:
        src, _ = source_for(cut)
        asset = kitkat.import_asset(pid, str(src.resolve()))
        start = int(round(cut["start_s"] * 1000))
        dur = int(round((cut["end_s"] - cut["start_s"]) * 1000))
        cmds.append(kitkat.cmd_add_clip(
            vt, f"cut{cut['id']:02d}", "image", asset["id"], start, dur))

    if plan["bgm"]:
        a = kitkat.import_asset(pid, str(plan["bgm"].resolve()))
        dur = int(round(plan["seconds"] * 1000))
        # 오디오 클립은 이미지보다 네 칸을 더 요구한다 — in·out(원본에서 자를 구간)
        # 과 speed·volume. 서버 검증으로 확인한 최소 모양이다.
        cmds.append(kitkat.cmd_add_clip(
            at, "bgm", "audio", a["id"], 0, dur,
            **{"in": 0, "out": dur, "speed": 1, "volume": 1}))

    kitkat.apply_commands(pid, cmds)
    return pid, kitkat.editor_url(pid)


def run(dry: bool = True) -> None:
    plan = check()

    print("[B 애니매틱]  kitkat")
    print(f"  길이      {plan['seconds']}초 · {W}×{H} · {FPS}fps")
    print(f"  바닥 트랙 {len(plan['base'])}컷")
    for c in plan["base"]:
        src, kind = source_for(c)
        mark = " " if src.exists() else "✗"
        print(f"    {mark} 컷{c['id']:>2}  {c['start_s']:>6.2f}–{c['end_s']:<6.2f} "
              f"({c['end_s'] - c['start_s']:.2f}s)  {kind:<9} {rel(src)}")
    if plan["overlays"]:
        print(f"  오버레이  {len(plan['overlays'])}컷 — 분할화면은 C 단계에서 얹는다")
    print(f"  음악      {rel(plan['bgm']) if plan['bgm'] else '(없음)'}")
    print(f"  결과      {rel(ANIMATIC)}")

    if dry:
        print("  → 시험 실행(--dry). kitkat 호출 안 함.")
        return
    if plan["missing"]:
        print(f"  ⚠ 이미지 {len(plan['missing'])}개가 없어서 그 컷은 빠집니다")

    pid, url = build(plan)
    print(f"  프로젝트  {pid}")
    print(f"  편집기    {url}   ← 브라우저로 열면 사람이 직접 고칠 수 있습니다")

    job = kitkat.render(pid, format="mp4", width=W, height=H)
    print(f"  렌더 중…  job {job}")
    res = kitkat.wait_job(job)

    # 결과는 res["result"]["path"] 에 있다 (url 은 서버 기준 상대경로).
    src = (res.get("result") or {}).get("path")
    if src:
        shutil.copyfile(src, ANIMATIC)
        print(f"  ✅ 완료    {rel(ANIMATIC)}  ({ANIMATIC.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"  ⚠ 렌더는 끝났는데 결과 경로를 못 찾았습니다: {res}")
    print("  → 원본과 나란히 놓고 «길이와 흐름이 맞나» 보세요.")
