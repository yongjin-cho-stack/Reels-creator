"""`.env` 를 읽는다.

열쇠는 **환경변수로만** 다룬다. 명령줄 인자나 URL 에 넣지 않는다 —
그 둘은 실패하면 자기 자신을 화면에 그대로 뱉는다.
그래서 이 파일은 값을 **절대 출력하지 않는다.** 길이만 말한다.
"""

from __future__ import annotations

import os

from .paths import ROOT

_LOADED = False


def load() -> None:
    """레포 루트의 .env 를 환경변수로 올린다. 이미 있는 값은 안 덮는다."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v and k not in os.environ:
            os.environ[k] = v


def get(name: str) -> str | None:
    load()
    v = os.environ.get(name)
    return v or None


def require(name: str, hint: str) -> str:
    v = get(name)
    if not v:
        raise RuntimeError(f"{name} 가 없습니다.\n  → {hint}")
    return v


def describe(name: str) -> str:
    """열쇠가 있는지 **값 없이** 말한다."""
    v = get(name)
    return f"{len(v)}자" if v else "없음"
