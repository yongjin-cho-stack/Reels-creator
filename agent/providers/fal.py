"""fal.ai 배선 — 아직 껍데기.

  나노바나나 프로  fal-ai/nano-banana-pro/edit
    image_urls    최대 14장 (URL 배열 — 로컬 경로 안 됨. 업로드 먼저)
    resolution    1K · 2K · 4K   ← 1K 와 2K 가 같은 값이라 2K 로 고정
    aspect_ratio  16:9
    num_images    1–4
    가격          장당 $0.15 (4K 는 두 배) · 웹검색 쓰면 +$0.015/요청

  클링           fal-ai/kling-video/v2.5-turbo/pro/image-to-video
    가격          5초 $0.35 · 추가 초당 $0.07
    ※ 제작A 담당
"""

MODEL_IMAGE = "fal-ai/nano-banana-pro/edit"
MODEL_VIDEO = "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"
PRICE_IMAGE = 0.15
PRICE_VIDEO_5S = 0.35


def upload(path):
    """로컬 파일 → 공개 URL. image_urls 가 URL 만 받는다."""
    raise NotImplementedError


def generate(prompt, image_urls, num_images=2, resolution="2K", aspect_ratio="16:9"):
    raise NotImplementedError
