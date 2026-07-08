"""
YouTube Data API v3 — Shorts 업로드 모듈

준비 사항:
  1. Google Cloud Console → 프로젝트 생성
  2. YouTube Data API v3 활성화
  3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
  4. client_secrets.json 다운로드 → 프로젝트 루트 또는 YOUTUBE_CLIENT_SECRETS 환경변수 경로

최초 실행 시 브라우저 인증 필요 → token.json 생성됨 (이후 자동 갱신)

환경변수:
  YOUTUBE_CLIENT_SECRETS  클라이언트 시크릿 JSON 경로 (기본: client_secrets.json)
  YOUTUBE_TOKEN           토큰 저장 경로 (기본: .youtube_token.json)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE = "youtube"
API_VERSION = "v3"


# ── 인증 ──────────────────────────────────────────────────────────
def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets_path = Path(os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json"))
    token_path   = Path(os.environ.get("YOUTUBE_TOKEN", ".youtube_token.json"))

    if not secrets_path.exists():
        raise RuntimeError(
            f"client_secrets.json 없음: {secrets_path}\n"
            "Google Cloud Console → OAuth 2.0 클라이언트 ID → JSON 다운로드 후 배치하세요.\n"
            "환경변수 YOUTUBE_CLIENT_SECRETS로 경로 변경 가능."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("YouTube 토큰 갱신 완료")
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("YouTube OAuth 인증 완료")
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _build_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    return build(API_SERVICE, API_VERSION, credentials=creds)


# ── 업로드 ────────────────────────────────────────────────────────
def upload_shorts(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "22",   # People & Blogs
) -> str:
    """
    YouTube Shorts 업로드.
    제목/설명에 #Shorts 태그 자동 추가.
    returns: video_id
    """
    from googleapiclient.http import MediaFileUpload

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"영상 파일 없음: {video_path}")

    # #Shorts는 제목 또는 설명에 포함되어야 Shorts로 인식
    if "#Shorts" not in title and "#Shorts" not in description:
        description = "#Shorts\n\n" + description

    default_tags = ["NEXTPICK", "성장주", "주식스크리너", "한국주식", "Shorts"]
    final_tags   = list(dict.fromkeys((tags or []) + default_tags))  # 중복 제거

    body = {
        "snippet": {
            "title":       title[:100],      # YouTube 제목 최대 100자
            "description": description[:5000],
            "tags":        final_tags,
            "categoryId":  category_id,
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB 청크
    )

    logger.info("YouTube 업로드 시작: %s (%s)", video_path.name, _human_size(video_path))
    service = _build_service()
    request = service.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            logger.info("업로드 진행: %d%%", pct)

    video_id = response["id"]
    logger.info("YouTube 업로드 완료: https://youtu.be/%s", video_id)
    return video_id


def _human_size(p: Path) -> str:
    s = p.stat().st_size
    if s >= 1_000_000: return f"{s/1_000_000:.1f}MB"
    if s >= 1_000:     return f"{s/1_000:.1f}KB"
    return f"{s}B"


# ── 공개 진입점 ───────────────────────────────────────────────────
def post_to_youtube(video_path: Path, stocks: list[dict], score_date) -> str:
    """
    Shorts 업로드 래퍼.
    returns: video_id
    """
    ds    = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    names = " · ".join(s["name"] for s in stocks[:5])

    title = f"{ds} CAN SLIM TOP 5 성장주 | {names}"

    desc_lines = [
        f"📊 {ds} CAN SLIM 성장주 TOP 5",
        "",
        "7대 성장주 기준으로 자동 선별한 오늘의 주도주입니다.",
        "",
    ]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, s in enumerate(stocks[:5]):
        comp = float(s["composite"] or 0)
        desc_lines.append(f"{medals[i]} {s['name']}({s['ticker']})  {comp:.0f}점")
    desc_lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🔗 더 자세한 분석: https://k-stock-score.vercel.app",
        "",
        "⚠️ 투자 참고용. 손실 책임은 투자자 본인에게 있습니다.",
        "",
        "#NEXTPICK #성장주 #주식스크리너 #한국주식 #주식공부 #성장주투자 #Shorts",
    ]

    tags = [s["name"] for s in stocks[:5]] + [
        s["ticker"] for s in stocks[:5]
    ] + ["NEXTPICK", "성장주", "한국주식", "주식공부", "성장주투자"]

    return upload_shorts(video_path, title, "\n".join(desc_lines), tags)


# ── 직접 실행 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="YouTube Shorts 업로드")
    parser.add_argument("video", help="업로드할 MP4 경로")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from etl.sns_publisher.card_generator import fetch
    stocks = fetch(5)
    score_date = stocks[0]["score_date"]

    video_id = post_to_youtube(Path(args.video), stocks, score_date)
    print(f"\n업로드 완료: https://youtu.be/{video_id}")
