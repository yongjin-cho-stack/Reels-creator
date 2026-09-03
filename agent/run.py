"""명령 진입점 — 단계 하나 = 명령 하나.

    python -m agent.run keycut    [--go]
    python -m agent.run image     [--go]
    python -m agent.run animatic  [--go]
    python -m agent.run edit      [--go]
    python -m agent.run all

기본은 **시험 실행**이다. 입력이 갖춰졌는지만 보고 계획을 찍는다.
실제로 돌리려면 `--go` 를 붙인다. 돈이 나가는 단계는 상한 검사를 거친다.
"""

from __future__ import annotations

import argparse
import sys

# Windows 기본 콘솔은 cp949 라 한글·기호에서 죽는다. 출력만 UTF-8 로 돌린다.
for _s in (sys.stdout, sys.stderr):
    try:
        if (_s.encoding or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from . import cost
from .steps import animatic, edit, image, keycut, polish, video
from .steps._common import StepBlocked

STEPS = {
    "keycut": ("A · 키컷 생성", keycut),
    "image": ("D · 컷 이미지", image),
    "video": ("제작A · 영상화", video),
    "animatic": ("B · 애니매틱", animatic),
    "edit": ("C-1 · 기계적 조립", edit),
    "polish": ("C-2 · 다듬기", polish),
}
ORDER = ["keycut", "image", "video", "animatic", "edit", "polish"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agent.run")
    ap.add_argument("step", choices=[*STEPS, "all"])
    ap.add_argument("--go", action="store_true", help="실제로 실행 (기본은 시험 실행)")
    ap.add_argument("--only-cut", type=int, default=None,
                    help="컷 하나만 (파일럿). 돈을 조금만 쓰고 확인할 때")
    args = ap.parse_args(argv)

    names = ORDER if args.step == "all" else [args.step]
    blocked = 0

    for i, name in enumerate(names):
        label, mod = STEPS[name]
        if i:
            print()
        print(f"── {label} " + "─" * (52 - len(label)))
        try:
            mod.run(dry=not args.go, only=args.only_cut)
        except StepBlocked as e:
            blocked += 1
            print(f"  ⏸ 멈춤 — {e}")
            if args.step != "all":
                return 1
        except cost.CostLimitExceeded as e:
            print(f"  ⛔ {e}")
            return 2
        except NotImplementedError as e:
            print(f"  … 아직 안 만듦: {e}")

    spent = cost.total()
    print()
    print(f"── 합계 " + "─" * 46)
    print(f"  지금까지 쓴 돈  ${spent:.2f}")
    if blocked:
        print(f"  멈춘 단계       {blocked}개 (위의 ⏸ 참고)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
