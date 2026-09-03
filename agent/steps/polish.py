"""단계 C-2 · 다듬기 — 받은 영상을 «보고» 판단해서 고친다.

C-1(edit.py)은 받은 영상이 어떻든 똑같이 동작한다. 그래서 규칙으로 적을 수 있다.
그런데 클링 결과는 매번 다르다 — 색이 튀고, 5초 중 쓸 만한 건 1초뿐이고,
앞부분에서 물체가 녹아 있다. 그걸 다루려면 **보고 판단해야** 한다.

## 네 걸음

    1  measure()   재료를 모은다   — 프레임 · 스코프 · 경계 쌍
    2  decide()    판단한다        — ★ 여기가 LLM 자리다
    3  apply()     명령으로 옮긴다 — trim · match_color · 전환
    4  verify()    다시 재서 나아졌는지 본다

**2번이 이 파일의 이유다.** 지금은 사람(또는 이 세션의 Claude)이 measure 결과를
보고 손으로 정한다. 그 판단을 규칙으로 적으면 그 자리에 LLM 호출이 들어간다.

## 무엇을 판단하나

  · **어디를 잘라 쓸까**  클링은 5초를 주는데 우리 컷은 1~3초다.
                          지금 C-1 은 무조건 앞에서부터 쓴다.
  · **색이 튀나**         기준 컷 하나를 정하고 나머지를 맞춘다 (match_color)
  · **전환을 뭘 걸까**    앞 컷 끝 프레임과 뒤 컷 첫 프레임을 대조한다
  · **후보 중 어느 것**   컷당 2개 중 1차 추리기

## 사람에게 남기는 것

**«움직임이 어색한가»** 는 프레임으로 판단하기 어렵다. 그건 게이트로 남긴다.

## 전환에 대해 알아낸 것 (2026-09-03, 실제로 렌더해 보고)

**① kitkat 의 `dissolve` 는 크로스페이드가 아니다.**
화면을 격자로 나눠 «칸마다 원이 자라는» 점무늬 전환이다(transitions.tsx 의 주석).
의도된 스타일이고, 잔잔한 광고 톤에는 안 맞는다. 부드럽게 넘기려면 **`fade`** 다.

**② 전환을 앞뒤 양쪽에 걸면 한 프레임이 새까매진다.**
`transitionOut`(앞 컷)과 `transitionIn`(뒤 컷)을 다 걸면, 둘 다 반투명한 순간에
배경이 비친다. **들어오는 쪽에만** 건다.

**③ 한 트랙 위의 붙어 있는 클립끼리는 «진짜 크로스페이드»가 안 된다.**
앞 컷이 딱 끊기고 뒤 컷이 **검정에서 밝아진다**. 앞 컷이 이미 끝났기 때문이다.
진짜로 겹쳐 넘기려면 뒤 컷을 **전환 길이만큼 일찍, 다른 트랙에** 놓아야 하고,
그러려면 소스에 그만큼 **여유(slack)** 가 있어야 한다.

  · 지금 가짜 영상은 여유가 0.03초뿐이라 못 한다.
  · **진짜 클링 영상은 컷당 5초라 여유가 넉넉하다** — 그때 다시 볼 일이다.

그래서 measure() 가 재는 slack_seconds 는 «어디를 잘라 쓸까» 뿐 아니라
«크로스페이드를 걸 수 있나» 도 함께 답한다.
"""

from __future__ import annotations

import json
import subprocess

from ..paths import ROOT, rel
from ._common import load_cuts, timeline
from .edit import source_for

POLISH = ROOT / "polish"
FRAMES = POLISH / "frames"
PAIRS = POLISH / "pairs"


def probe_duration(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out or 0)


def grab(src, t: float, dst, width: int = 640) -> bool:
    """한 시각의 프레임 한 장."""
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(t, 0):.3f}",
         "-i", str(src), "-frames:v", "1", "-vf", f"scale={width}:-2",
         str(dst), "-y"], capture_output=True)
    return r.returncode == 0 and dst.exists()


def measure() -> dict:
    """판단 재료를 모은다. 여기서는 **아무 결정도 하지 않는다.**"""
    FRAMES.mkdir(parents=True, exist_ok=True)
    PAIRS.mkdir(parents=True, exist_ok=True)
    cuts = load_cuts()
    base = timeline(cuts)

    report = {"cuts": [], "boundaries": []}

    # ── 컷마다: 소스 길이 · 우리가 쓸 길이 · 앞/중간/뒤 프레임
    for cut in cuts["cuts"]:
        src, kind = source_for(cut)
        if not src.exists():
            continue
        src_dur = probe_duration(src)
        need = round(cut["end_s"] - cut["start_s"], 3)
        shots = {}
        for tag, t in (("a", 0.10), ("b", src_dur / 2), ("c", max(src_dur - 0.15, 0))):
            p = FRAMES / f"cut{cut['id']:02d}_{tag}.jpg"
            if grab(src, t, p):
                shots[tag] = rel(p)
        report["cuts"].append({
            "id": cut["id"], "source": rel(src), "kind": kind,
            "source_seconds": round(src_dur, 3),
            "need_seconds": need,
            "slack_seconds": round(src_dur - need, 3),   # 버릴 수 있는 여유
            "frames": shots,
        })

    # ── 경계마다: 앞 컷 끝 · 뒤 컷 첫 — 전환을 뭘 걸지 판단하는 재료
    for prev, nxt in zip(base, base[1:]):
        ps, _ = source_for(prev)
        ns, _ = source_for(nxt)
        if not (ps.exists() and ns.exists()):
            continue
        a = PAIRS / f"b{prev['id']:02d}-{nxt['id']:02d}_out.jpg"
        b = PAIRS / f"b{prev['id']:02d}-{nxt['id']:02d}_in.jpg"
        grab(ps, max(probe_duration(ps) - 0.15, 0), a)
        grab(ns, 0.10, b)
        report["boundaries"].append({
            "at_s": nxt["start_s"], "from": prev["id"], "to": nxt["id"],
            "out": rel(a), "in": rel(b),
        })

    (POLISH / "measure.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


# ─────────────────────────────────────────────────────────────────
# 2. decide — ★ 여기가 LLM 자리다
# ─────────────────────────────────────────────────────────────────
#
# 아래 표는 2026-09-03 에 measure 결과(경계 프레임 7쌍)를 **보고 정한 것**이다.
# 판단이 아니라 판단의 **결과**이므로, 규칙을 같이 적어 둔다 —
# 다음에 다른 영상이 와도 같은 규칙으로 다시 정하면 된다.
#
#   전환 규칙
#     · 앞뒤가 **같은 공간**이면 하드컷 (전환 없음)
#     · **공간이 바뀌면** dissolve
#     · 밝기까지 크게 바뀌면 dissolve 를 길게
#
#   트림 규칙
#     · 컷의 «중요한 순간»이 끝에 있으면 **앞을 버린다**
#     · 앞에 있으면 뒤를 버린다
#     · 모르면 가운데를 쓴다
#
TRANSITIONS = {
    # (앞 컷, 뒤 컷): (전환, 길이 ms)
    (3, 4): ("fade", 400),   # 실내(어둡고 따뜻) → 제주 항공샷(밝은 청록). 가장 크게 튄다
    (4, 8): ("fade", 300),   # 항공샷 → 옹기(어두운 갈색). 밝음 → 어두움
    # 나머지 다섯 경계는 같은 공간이라 하드컷으로 둔다:
    #   1→2 클로즈업으로 파고듦 · 2→3 같은 톤 · 8→9 이어지는 행동
    #   9→10 같은 방 · 10→11 같은 방
}

# 끝이 중요한 컷 — 여유를 **앞에서** 버린다.
# 컷 1은 「바다가 유화로 변하며 줌아웃 → 화가 뒷모습이 드러난다」라 끝이 알맹이다.
TRIM_FROM_HEAD = {1}


def decide(rep: dict) -> dict:
    """재료를 보고 결정한다. 지금은 위 표를 읽지만, 자리는 여기다."""
    trims, clamps = {}, {}
    for c in rep["cuts"]:
        slack = c["slack_seconds"]
        if slack < 0:
            # 소스가 필요한 길이보다 짧다 → 끝이 검게 나오거나 얼어붙는다.
            clamps[c["id"]] = round(c["source_seconds"], 3)
        elif c["id"] in TRIM_FROM_HEAD and slack > 0.05:
            trims[c["id"]] = round(slack, 3)      # 앞에서 이만큼 버린다
    # JSON 은 튜플 키를 못 담는다 → 목록으로 편다.
    trans = [{"from": a, "to": b, "type": ty, "duration_ms": ms}
             for (a, b), (ty, ms) in TRANSITIONS.items()]
    return {"transitions": trans, "trims": trims, "clamps": clamps}


def run(dry: bool = True) -> None:
    print("[C-2 다듬기]  재료 모으기")
    rep = measure()

    print(f"  컷 {len(rep['cuts'])}개")
    print(f"    {'컷':>4} {'소스':>7} {'필요':>7} {'여유':>7}   버릴 수 있는 만큼")
    for c in rep["cuts"]:
        bar = "▓" * min(int(c["slack_seconds"] * 4), 24)
        print(f"    {c['id']:>4} {c['source_seconds']:>7.2f} {c['need_seconds']:>7.2f} "
              f"{c['slack_seconds']:>7.2f}   {bar}")
    print(f"  경계 {len(rep['boundaries'])}개")
    print(f"  재료      {rel(POLISH)}/  (frames · pairs · measure.json)")

    plan = decide(rep)
    (POLISH / "decide.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print()
    print("  판단")
    for tr in plan["transitions"]:
        print(f"    전환   컷{tr['from']:>2} → 컷{tr['to']:<2}   "
              f"{tr['type']} {tr['duration_ms']}ms")
    if not plan["transitions"]:
        print("    전환   없음 (전부 하드컷)")
    for cid, s in plan["trims"].items():
        print(f"    트림   컷{cid:>2}          앞에서 {s}초 버림 (끝이 중요한 컷)")
    for cid, s in plan["clamps"].items():
        print(f"    ⚠ 길이  컷{cid:>2}          소스가 짧다 → {s}초로 줄임")
    print(f"  결정      {rel(POLISH / 'decide.json')}")
    print("  → 다음: apply — 이 결정을 kitkat 명령으로 옮긴다")
