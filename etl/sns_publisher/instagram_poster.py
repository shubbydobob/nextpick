"""
Meta Graph API — Instagram 포스팅 모듈

준비 사항:
  1. Meta for Developers → 앱 생성
  2. Instagram Graph API 권한: instagram_basic, instagram_content_publish
  3. 장기 액세스 토큰 발급 (60일, 자동 갱신 가능)
  4. 환경변수 설정:
       INSTAGRAM_USER_ID = 숫자 ID
       INSTAGRAM_TOKEN   = 액세스 토큰
  5. 이미지는 반드시 공개 URL 필요 → imgbb 업로드 재사용

API 흐름:
  1. 미디어 컨테이너 생성 (POST /{user_id}/media)
  2. 게시 (POST /{user_id}/media_publish)
"""
import os
import time
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v19.0"


# ── 인증 정보 ────────────────────────────────────────────────────
def _get_credentials() -> tuple[str, str]:
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    token   = os.environ.get("INSTAGRAM_TOKEN")
    if not user_id or not token:
        raise RuntimeError(
            "환경변수 미설정:\n"
            "  INSTAGRAM_USER_ID = Instagram 비즈니스/크리에이터 계정 ID\n"
            "  INSTAGRAM_TOKEN   = 액세스 토큰\n"
            "Meta for Developers(developers.facebook.com)에서 발급하세요."
        )
    return user_id, token


# ── 미디어 컨테이너 생성 ─────────────────────────────────────────
def create_media_container(user_id: str, token: str, image_url: str, caption: str) -> str:
    """Instagram 이미지 미디어 컨테이너 생성 → creation_id 반환."""
    params = {
        "access_token": token,
        "image_url": image_url,
        "caption": caption,
        "media_type": "IMAGE",
    }
    res = requests.post(
        f"{GRAPH_API}/{user_id}/media",
        data=params,
        timeout=30,
    )
    if not res.ok:
        logger.error("Instagram 컨테이너 생성 실패: %s", res.text)
        res.raise_for_status()
    creation_id = res.json()["id"]
    logger.info("Instagram 컨테이너 생성 완료: %s", creation_id)
    return creation_id


# ── 컨테이너 상태 확인 ───────────────────────────────────────────
def _wait_for_container(user_id: str, token: str, creation_id: str, max_wait: int = 120) -> bool:
    """컨테이너가 FINISHED 상태가 될 때까지 폴링."""
    for elapsed in range(0, max_wait, 10):
        time.sleep(10)
        res = requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        if not res.ok:
            continue
        status = res.json().get("status_code", "")
        logger.debug("컨테이너 상태: %s (%ds 경과)", status, elapsed + 10)
        if status == "FINISHED":
            return True
        if status == "ERROR":
            logger.error("컨테이너 처리 오류: %s", res.json())
            return False
    logger.warning("컨테이너 상태 확인 시간 초과 (%ds)", max_wait)
    return False


# ── 게시 ─────────────────────────────────────────────────────────
def publish_media(user_id: str, token: str, creation_id: str) -> str:
    """컨테이너 게시 → media_id 반환."""
    res = requests.post(
        f"{GRAPH_API}/{user_id}/media_publish",
        data={"access_token": token, "creation_id": creation_id},
        timeout=30,
    )
    if not res.ok:
        logger.error("Instagram 게시 실패: %s", res.text)
        res.raise_for_status()
    media_id = res.json()["id"]
    logger.info("Instagram 게시 완료: media_id=%s", media_id)
    return media_id


# ── 공개 진입점 ──────────────────────────────────────────────────
def post_to_instagram(caption: str, image_path: Path | None = None) -> str:
    """
    Instagram에 포스팅.
    image_path 있으면 imgbb 업로드 후 이미지 포스트.
    없으면 캡션만으로 시도 (Instagram은 이미지 필수이므로 에러 발생 가능).

    returns: media_id
    """
    user_id, token = _get_credentials()

    if image_path is None or not Path(image_path).exists():
        raise ValueError("Instagram 포스팅에는 이미지가 필요합니다. image_path를 지정하세요.")

    # imgbb 업로드 (threads_poster.py와 공유)
    from .threads_poster import upload_image_imgbb
    image_url = upload_image_imgbb(Path(image_path))

    creation_id = create_media_container(user_id, token, image_url, caption)

    # 컨테이너 준비 대기 (Instagram은 처리 시간이 필요)
    _wait_for_container(user_id, token, creation_id)

    media_id = publish_media(user_id, token, creation_id)
    return media_id


# ── 직접 실행 ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from etl.sns_publisher.card_generator import run as generate

    print("카드 생성 중...")
    result = generate()
    caption = Path(result["caption"]).read_text(encoding="utf-8")
    image_path = Path(result["image"])

    print(f"이미지: {image_path}")
    print(f"캡션 길이: {len(caption)}자")

    confirm = input("\nInstagram에 게시하시겠습니까? (y/N): ").strip().lower()
    if confirm == "y":
        media_id = post_to_instagram(caption, image_path)
        print(f"\n게시 완료: media_id={media_id}")
    else:
        print("취소됨.")
