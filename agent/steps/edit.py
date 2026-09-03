"""단계 C · 최종 편집 — 영상 조각을 조립해 final.mp4.

두 층으로 나뉜다.

  C-1  기계적 조립   cuts.json 대로 붙이고 분할화면을 얹는다   ← 이 파일
  C-2  다듬기        받은 영상을 보고 판단해서 고친다          ← polish.py

C-1 은 «받은 영상이 어떻든 똑같이» 동작한다. 그래서 규칙으로 적을 수 있다.
클링 결과가 매번 다른 것(색이 튀고, 5초 중 쓸 만한 건 1초뿐이고, 앞부분이
녹아 있는)을 다루는 건 C-2 의 몫이다.

B(애니매틱)의 build 를 그대로 닮았다 — kind 가 image → video 로 바뀌고
분할화면이 붙는다.

## 분할화면

컷 4가 배경(제주 항공샷)이고 컷 5·6·7 이 그 위에 시각차를 두고 열리는 창이다.
자리는 원본 1920×1080 프레임에서 잰 값이다.
"""

from __future__ import annotations

import shutil

import json

from ..paths import BGM, FAKE_VIDEOS, FINAL, ROOT, VIDEOS, rel
from ..providers import kitkat
from ._common import load_cuts, overlays, timeline, total_seconds
from .animatic import FPS, H, W, pick_bgm

# 분할화면 창의 자리 — 원본 프레임에서 잰 값 (x, y, w, h), 왼쪽 위 기준
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


def overlay_transform(cut_id: int) -> dict:
    """창 하나를 «어디에 얼마나 크게» 놓을지.

    ⚠️ **x·y 는 픽셀이 아니라 «캔버스 대비 비율»이다.** 렌더러가 이렇게 쓴다:

        left = (canvasW - boxW) / 2 + x * canvasW

    픽셀을 넣으면 화면 밖으로 날아가서 **아무것도 안 보인다**(에러도 안 난다).
    처음에 -355 를 넣었다가 -355×1920 = -68만 px 로 사라졌다.

    scale 은 «캔버스에 맞춘 크기» 기준의 배율이다. 소스가 1920×1080 이면
    scale 0.44 가 곧 화면 폭의 44% 다.
    """
    x, y, w, h = WINDOW_BOX[cut_id]
    return {
        "scale": round(w / W, 4),
        "x": round(((x + w / 2) - W / 2) / W, 4),
        "y": round(((y + h / 2) - H / 2) / H, 4),
        "rotation": 0,          # 네 칸이 다 있어야 한다 (서버 검증)
    }


def load_polish() -> dict:
    """C-2 의 결정을 읽는다. 없으면 «아무것도 안 고침» 이다."""
    p = ROOT / "polish" / "decide.json"
    if not p.exists():
        return {"transitions": [], "trims": {}, "clamps": {}, "look": []}
    return json.loads(p.read_text(encoding="utf-8"))


def check() -> dict:
    cuts = load_cuts()
    ready, missing = [], []
    for cut in cuts["cuts"]:
        src, kind = source_for(cut)
        (ready if src.exists() else missing).append((cut, src, kind))
    return {
        "cuts": cuts, "base": timeline(cuts), "overlays": overlays(cuts),
        "ready": ready, "missing": missing,
        "bgm": pick_bgm(), "seconds": total_seconds(cuts),
        "polish": load_polish(),
    }


def build(plan: dict) -> tuple[str, str]:
    doc = kitkat.create_project("오설록 17초 · 최종")
    pid = doc["id"]
    vt = kitkat.track_of(doc, "video")
    at = kitkat.track_of(doc, "audio")
    cmds = [kitkat.cmd_settings(W, H, FPS)]

    # ── 바닥 트랙 (C-2 의 결정을 반영한다)
    pol = plan["polish"]
    trims = {int(k): v for k, v in pol.get("trims", {}).items()}
    clamps = {int(k): v for k, v in pol.get("clamps", {}).items()}
    t_in = {tr["to"]: tr for tr in pol.get("transitions", [])}
    t_out = {tr["from"]: tr for tr in pol.get("transitions", [])}

    for cut in plan["base"]:
        src, _ = source_for(cut)
        if not src.exists():
            continue
        a = kitkat.import_asset(pid, str(src.resolve()))
        cid = cut["id"]
        start = int(round(cut["start_s"] * 1000))
        dur = int(round((cut["end_s"] - cut["start_s"]) * 1000))
        if cid in clamps:                      # 소스가 짧다 → 있는 만큼만
            dur = min(dur, int(clamps[cid] * 1000))
        head = int(round(trims.get(cid, 0) * 1000))   # 앞에서 버릴 만큼
        extra = {"in": head, "out": head + dur, "speed": 1, "volume": 0}
        if pol.get("look"):
            extra["effects"] = [dict(e) for e in pol["look"]]   # 전 컷에 같은 룩
        if cid in t_in:
            extra["transitionIn"] = {"type": t_in[cid]["type"],
                                     "duration": t_in[cid]["duration_ms"]}
        # transitionOut 은 걸지 않는다 — 양쪽에 걸면 둘 다 반투명한 순간에
        # 배경(검정)이 비쳐서 한 프레임이 새까맣게 된다. 들어오는 쪽만 건다.
        cmds.append(kitkat.cmd_add_clip(
            vt, f"cut{cid:02d}", "video", a["id"], start, dur, **extra))

    # ── 분할화면 — 창마다 트랙을 하나씩 더 쌓는다 (겹치니까 같은 트랙에 못 넣는다)
    for cut in plan["overlays"]:
        src, _ = source_for(cut)
        if not src.exists():
            continue
        tid = f"ov{cut['id']}"
        cmds.append({"type": "addTrack",
                     "track": {"id": tid, "kind": "video",
                               "name": f"분할창{cut['id']}", "clips": []}})
        a = kitkat.import_asset(pid, str(src.resolve()))
        start = int(round(cut["start_s"] * 1000))
        dur = int(round((cut["end_s"] - cut["start_s"]) * 1000))
        cmds.append(kitkat.cmd_add_clip(
            tid, f"cut{cut['id']:02d}", "video", a["id"], start, dur,
            **{"in": 0, "out": dur, "speed": 1, "volume": 0,
               "transform": overlay_transform(cut["id"])}))

    # ── 음악
    if plan["bgm"]:
        a = kitkat.import_asset(pid, str(plan["bgm"].resolve()))
        dur = int(round(plan["seconds"] * 1000))
        cmds.append(kitkat.cmd_add_clip(
            at, "bgm", "audio", a["id"], 0, dur,
            **{"in": 0, "out": dur, "speed": 1, "volume": 1}))

    kitkat.apply_commands(pid, cmds)
    return pid, kitkat.editor_url(pid)


def run(dry: bool = True) -> None:
    plan = check()

    print("[C 최종 편집]  kitkat")
    print(f"  길이      {plan['seconds']}초")
    print(f"  준비된 컷 {len(plan['ready'])} / {len(plan['ready']) + len(plan['missing'])}")
    for cut, src, kind in plan["ready"]:
        tag = "분할창" if cut["id"] in WINDOW_BOX else "바닥"
        print(f"    · 컷{cut['id']:>2}  {tag:<4} {kind:<8} {rel(src)}")
    for cut, src, kind in plan["missing"]:
        print(f"    ✗ 컷{cut['id']:>2}  영상 없음")

    if plan["overlays"]:
        print("  분할화면 (컷 4 위에)")
        for c in plan["overlays"]:
            t = overlay_transform(c["id"])
            print(f"      컷{c['id']:>2}  {c['start_s']:>6.2f}s 등장  "
                  f"scale {t['scale']}  비율 ({t['x']:+.3f}, {t['y']:+.3f})")

    print(f"  결과      {rel(FINAL)}")
    if dry:
        print("  → 시험 실행(--dry). kitkat 호출 안 함.")
        return

    pid, url = build(plan)
    print(f"  프로젝트  {pid}")
    print(f"  편집기    {url}")

    job = kitkat.render(pid, format="mp4", width=W, height=H)
    print(f"  렌더 중…  job {job}")
    res = kitkat.wait_job(job)
    src = (res.get("result") or {}).get("path")
    if src:
        shutil.copyfile(src, FINAL)
        print(f"  ✅ 완료    {rel(FINAL)}  ({FINAL.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"  ⚠ 결과 경로를 못 찾았습니다: {res}")
