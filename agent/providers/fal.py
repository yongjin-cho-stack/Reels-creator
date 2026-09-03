"""fal.ai 배선 — 이미지(나노바나나 프로)와 영상(클링).

    나노바나나 프로   fal-ai/nano-banana-pro/edit
      image_urls    참조 이미지 **최대 14장**. URL 만 받는다 → 먼저 올려야 한다
      resolution    1K · 2K · 4K   ← 1K 와 2K 가 **같은 값**이라 2K 로 고정
      aspect_ratio  16:9
      num_images    1–4
      가격          장당 $0.15 (4K 는 두 배) · 웹검색을 쓰면 요청당 +$0.015

    클링             fal-ai/kling-video/v2.5-turbo/pro/image-to-video
      가격          5초 $0.35 · 추가 초당 $0.07
      ※ 제작A 담당

## SDK 를 안 쓰고 HTTP 로 직접 부른다 (2026-09-03)

`fal-client` 1.0.1 이 업로드를 `?storage_type=gcs` 로 부르는데 서버가
**`{"detail":"Invalid storage type"}` 400** 을 준다. 그리고 그 버전에서 안 올라간다.
파라미터만 빼면 200 이라 직접 부르는 쪽이 확실하다. 의존성도 하나 준다.

  업로드   POST rest.fal.ai/storage/upload/initiate  {content_type, file_name}
              → {upload_url, file_url}
           PUT  upload_url  (파일 바이트)
           그다음 file_url 을 image_urls 에 쓴다
  생성     POST fal.run/<model>   (동기 · 끝날 때까지 기다린다)
  인증     Authorization: Key <FAL_KEY>

돈을 쓰는 호출은 **예외 없이** cost.guard 로 상한을 보고 cost.log 에 남긴다.
"""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path

from .. import cost
from ..env import describe, require

REST = "https://rest.fal.ai"
RUN = "https://fal.run"

MODEL_IMAGE = "fal-ai/nano-banana-pro/edit"
MODEL_VIDEO = "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"
PRICE_IMAGE = 0.15          # 장당 (1K·2K). 4K 는 두 배
PRICE_VIDEO_5S = 0.35

_UPLOADED: dict[str, str] = {}


class FalError(RuntimeError):
    """열쇠가 없거나 fal 이 거절했다. 무엇이 문제인지 그대로 담는다."""


def key_status() -> str:
    """열쇠가 있는지 **값 없이** 말한다."""
    return describe("FAL_KEY")


def _key() -> str:
    try:
        return require("FAL_KEY", ".env 에 FAL_KEY 를 넣으세요 (.env.example 참고)")
    except RuntimeError as e:
        raise FalError(str(e)) from None


def _post(url: str, body: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Key {_key()}", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return json.loads(f.read())
    except urllib.error.HTTPError as e:
        raise FalError(f"fal {e.code} — {e.read().decode()[:300]}") from None


def upload(path: str | Path) -> str:
    """로컬 파일 → 공개 URL.

    같은 레퍼런스를 여러 컷에서 쓰므로 한 번 올린 건 다시 안 올린다.
    """
    p = Path(path).resolve()
    key = str(p)
    if key in _UPLOADED:
        return _UPLOADED[key]

    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    init = _post(f"{REST}/storage/upload/initiate",
                 {"content_type": ctype, "file_name": p.name}, timeout=60)

    put = urllib.request.Request(init["upload_url"], data=p.read_bytes(),
                                 method="PUT", headers={"content-type": ctype})
    try:
        urllib.request.urlopen(put, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise FalError(f"업로드 실패 {e.code} — {e.read().decode()[:200]}") from None

    _UPLOADED[key] = init["file_url"]
    return init["file_url"]


def generate(prompt: str, image_urls: list[str], *, num_images: int = 2,
             resolution: str = "2K", aspect_ratio: str = "16:9",
             step: str = "?", target: str = "?") -> list[str]:
    """참조 이미지 + 주문서 → 만들어진 이미지 URL 목록. **돈이 나간다.**"""
    if not image_urls:
        raise ValueError("참조 이미지가 없습니다")
    if len(image_urls) > 14:
        raise ValueError(f"참조 이미지는 14장까지입니다 ({len(image_urls)}장)")

    usd = PRICE_IMAGE * num_images * (2 if resolution == "4K" else 1)
    cost.guard(usd)

    res = _post(f"{RUN}/{MODEL_IMAGE}", {
        "prompt": prompt,
        "image_urls": image_urls,
        "num_images": num_images,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    })
    urls = [im["url"] for im in (res.get("images") or [])]
    cost.log(step, "nano-banana-pro", target, len(urls), usd)
    return urls


def download(url: str, dst: str | Path) -> Path:
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dst)
    return dst
