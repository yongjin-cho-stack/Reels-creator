"""원본 17초를 컷별로 잘라 «가짜 영상» 을 만든다 — 제작A 를 안 기다리려고.

제작A 가 클링으로 만들 영상이 아직 없다. 그 자리에 원본 조각을 놓으면
C(최종 편집)를 끝까지 만들고 시험할 수 있다. 진짜 영상이 오면 파일만 갈아끼운다.

⚠️ 이건 **개발용 대체재**다. 최종 결과물에 쓰지 않는다.

원본 시간축(src_17s.mp4, 17.047초)은 cuts.json 의 시간축과 다르다 —
컷 1을 5.64→5.00초로 줄이면서 뒤가 0.64초씩 당겨졌기 때문이다.
그래서 여기서는 **원본 경계**를 쓴다.

분할화면(컷 4~7)은 원본에 이미 합성돼 있다. 그래서
  · 컷 4(배경) — 창이 열리기 전 구간을 늘려 쓴다
  · 컷 5·6·7 — 원본에서 각 창 영역을 잘라낸다
이렇게 해야 «따로 만들어진 소스를 우리가 얹는» 상태를 시험할 수 있다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC = Path(r"C:\Users\david\project\shorts\projects\osulloc-1m03\00_src\src_17s.mp4")
OUT = Path(__file__).resolve().parent.parent.parent / "videos_fake"

# (컷 id, 원본 시작, 원본 끝, 크롭 or None, 목표 길이 or None)
PLAN = [
    (1,  0.00,  5.64, None, None),
    (2,  5.64,  6.77, None, None),
    (3,  6.77,  7.91, None, None),
    # 배경 — 창이 열리기 전 0.69초를 2.83초로 늘린다
    (4,  7.91,  8.60, None, 2.83),
    # 분할창 — 원본에서 각 자리를 잘라낸다 (w:h:x:y)
    (5,  8.67, 10.74, "850:485:180:80", None),
    (6,  9.00, 10.74, "825:618:1030:222", None),
    (7, 10.00, 10.74, "650:350:280:565", None),
    (8, 10.74, 12.11, None, None),
    (9, 12.11, 13.41, None, None),
    (10, 13.41, 15.32, None, None),
    (11, 15.32, 17.05, None, None),
]


def run(cut_id, t0, t1, crop, stretch_to):
    dst = OUT / f"cut{cut_id:02d}.mp4"
    vf = []
    if crop:
        # 잘라낸 뒤 1920×1080 으로 되돌린다 — 클링 결과와 같은 크기로 맞추려는 것
        vf += [f"crop={crop}", "scale=1920:1080:flags=lanczos"]
    if stretch_to:
        vf.append(f"setpts={stretch_to / (t1 - t0):.4f}*PTS")
    args = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t0}", "-to", f"{t1}",
            "-i", str(SRC)]
    if vf:
        args += ["-vf", ",".join(vf)]
    args += ["-an", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", str(dst), "-y"]
    subprocess.run(args, check=True)
    return dst


def main():
    if not SRC.exists():
        sys.exit(f"원본이 없습니다: {SRC}")
    OUT.mkdir(exist_ok=True)
    for cut_id, t0, t1, crop, stretch in PLAN:
        d = run(cut_id, t0, t1, crop, stretch)
        note = "크롭" if crop else ("늘림" if stretch else "")
        print(f"  컷{cut_id:>2}  {t0:>5.2f}–{t1:<5.2f}  {d.stat().st_size / 1e6:>5.2f} MB  {note}")
    print(f"\n{len(PLAN)}개 만들었습니다 → {OUT}")


if __name__ == "__main__":
    main()
