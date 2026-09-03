"""kitkat 배선 — 로컬 편집 서버.

    cd ../kitkat && npm start        →  http://127.0.0.1:5757

계약은 문서가 아니라 **서버에 직접 물어서** 확인한 것이다(2026-09-03).

  POST /api/projects            {name}   → doc (id · revision · settings · tracks · assets)
      기본이 **1080×1920 세로**다. 가로는 setSettings 로 바꾼다.
      트랙 3개(video · text · audio)가 처음부터 들어 있다.
  POST /api/projects/:id/assets {path}   → {asset:{id,kind,src,name,width,height}, jobId}
      **로컬 절대경로**를 그대로 준다. 프록시·썸네일은 백그라운드로 돈다.
  POST /api/projects/:id/commands {commands, baseRevision?}
      각 명령에 `type` 필드. 22종 —
      addAsset removeAsset updateAsset · addTrack removeTrack reorderTrack setTrackProps
      addClip removeClip updateClip moveClip splitClip trimClip
      setClipSpeed setSpeedRamp setReversed freezeFrame · setKeyframes
      applyTextTemplate · duckTrack · renameProject setSettings
  POST /api/projects/:id/render {range?, proxy?, format?, width?, height?} → {jobId}
  GET  /api/jobs/:jobId                  → 진행 상태
  GET  /api/capabilities                 → 전환 51 · 효과 50 · 텍스트템플릿 90 · 라우드니스 5

클립의 최소 모양 (서버 검증으로 확인) — **시간 단위는 밀리초**:

    {"id": "c1", "kind": "image", "assetId": "...", "start": 0, "duration": 5000}

서버는 명령을 적용한 뒤 문서 전체를 검증하고, 틀리면 **어느 칸이 왜 틀렸는지**
짚어서 400 을 준다:  `INVALID_DOC: tracks.0.clips.0.id — Required`
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5757"


class KitkatDown(RuntimeError):
    """서버가 없다. 무엇을 하면 되는지 말해 준다."""


class KitkatError(RuntimeError):
    pass


def _call(method: str, path: str, body: dict | None = None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return json.loads(f.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", "")
        except Exception:
            msg = ""
        raise KitkatError(f"{method} {path} → {e.code}  {msg}") from None
    except OSError:
        raise KitkatDown(
            "kitkat 서버에 못 붙습니다 (http://127.0.0.1:5757).\n"
            "  → cd ../kitkat && npm start"
        ) from None


# ── 읽기 ───────────────────────────────────────────────────────────
def capabilities() -> dict:
    """전환·효과·템플릿 목록. 하드코딩하지 말고 이걸 읽는다."""
    return _call("GET", "/api/capabilities", timeout=20)


def get_project(pid: str) -> dict:
    d = _call("GET", f"/api/projects/{pid}")
    return d.get("doc", d)


# ── 만들기 ─────────────────────────────────────────────────────────
def create_project(name: str) -> dict:
    d = _call("POST", "/api/projects", {"name": name})
    return d.get("doc", d)


def import_asset(pid: str, abs_path: str) -> dict:
    """로컬 절대경로 → 에셋. {id, kind, src, name, width, height} 를 돌려준다."""
    return _call("POST", f"/api/projects/{pid}/assets", {"path": abs_path})["asset"]


def apply_commands(pid: str, commands: list[dict]) -> dict:
    return _call("POST", f"/api/projects/{pid}/commands", {"commands": commands})


def render(pid: str, **opts) -> str:
    """jobId 를 돌려준다. 완료는 wait_job 으로 기다린다."""
    return _call("POST", f"/api/projects/{pid}/render", opts)["jobId"]


def wait_job(job_id: str, timeout_s: int = 900, tick: float = 2.0) -> dict:
    """끝날 때까지 기다린다. 렌더는 몇 분 걸릴 수 있다."""
    deadline = time.time() + timeout_s
    while True:
        j = _call("GET", f"/api/jobs/{job_id}", timeout=30)
        st = j.get("status") or j.get("state")
        if st in ("succeeded", "done", "completed"):
            return j
        if st in ("failed", "error"):
            raise KitkatError(f"렌더 실패: {j.get('error') or j}")
        if time.time() > deadline:
            raise KitkatError(f"렌더가 {timeout_s}초 안에 안 끝났습니다 (job {job_id})")
        time.sleep(tick)


# ── 자주 쓰는 명령 ─────────────────────────────────────────────────
def cmd_settings(width: int, height: int, fps: int = 30) -> dict:
    return {"type": "setSettings",
            "settings": {"width": width, "height": height, "fps": fps}}


def cmd_add_clip(track_id: str, clip_id: str, kind: str, asset_id: str,
                 start_ms: int, duration_ms: int, **extra) -> dict:
    clip = {"id": clip_id, "kind": kind, "assetId": asset_id,
            "start": start_ms, "duration": duration_ms}
    clip.update(extra)
    return {"type": "addClip", "trackId": track_id, "clip": clip}


def track_of(doc: dict, kind: str) -> str:
    """기본 트랙 id. 프로젝트를 만들면 video · text · audio 가 이미 있다."""
    for t in doc["tracks"]:
        if t["kind"] == kind:
            return t["id"]
    raise KitkatError(f"'{kind}' 트랙이 없습니다")


def editor_url(pid: str) -> str:
    """사람이 브라우저로 열어 직접 고칠 주소."""
    return f"{BASE}/p/{pid}"
