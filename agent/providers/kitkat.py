"""kitkat 배선 — 아직 껍데기.

  로컬 편집 서버.  http://127.0.0.1:5757
    POST /api/projects                    프로젝트 만들기
    POST /api/projects/:id/commands       편집 명령 배치
    POST /api/projects/:id/render         렌더
    GET  /api/jobs/:jobId                 진행 상태
    GET  /api/capabilities                뭐가 되는지  ← 하드코딩하지 말고 이걸 먼저 부른다

  띄우기:  cd ../kitkat && npm start
"""

BASE = "http://127.0.0.1:5757"


def capabilities():
    """전환·효과·템플릿 목록. 하드코딩 대신 이걸 읽는다."""
    raise NotImplementedError


def create_project(name):
    raise NotImplementedError


def apply_commands(project_id, commands):
    raise NotImplementedError


def render(project_id, **opts):
    raise NotImplementedError
