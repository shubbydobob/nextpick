"""
Meta Threads API 포스팅 모듈

준비 사항:
  1. Meta for Developers → 앱 생성
  2. Threads API 권한: threads_basic, threads_content_publish
  3. 장기 액세스 토큰 발급 (60일, 자동 갱신 가능)
  4. 환경변수 설정:
       THREADS_USER_ID   = 숫자 ID (예: 1234567890)
       THREADS_TOKEN     = 액세스 토큰
  5. 이미지 포스팅은 공개 URL 필요 → 이미지 호스팅 필요
       (임시: imgbb 업로드 지원, IMGBB_API_KEY 환경변수)

API 흐름:
  1. 미디어 컨테이너 생성 (POST /threads)
  2. 게시 (POST /threads/{container_id}/publish)
"""
import os
import time
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

THREADS_API = "https://graph.threads.net/v1.0"


# ── 이미지 업로드 (imgbb) ────────────────────────────────────────
def upload_image_imgbb(image_path: Path) -> str:
    """이미지를 imgbb에 업로드하고 공개 URL 반환."""
    api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        raise RuntimeError("IMGBB_API_KEY 환경변수 미설정. imgbb.com에서 무료 API 키 발급 필요.")

    with open(image_path, "rb") as f:
        import base64
        data = base64.b64encode(f.read()).decode()

    res = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": data},
        timeout=30,
    )
    res.raise_for_status()
    url = res.json()["data"]["url"]
    logger.info("imgbb 업로드 완료: %s", url)
    return url


# ── Threads API ──────────────────────────────────────────────────
def _get_credentials() -> tuple[str, str]:
    user_id = os.environ.get("THREADS_USER_ID")
    token   = os.environ.get("THREADS_TOKEN")
    if not user_id or not token:
        raise RuntimeError(
            "환경변수 미설정:\n"
            "  THREADS_USER_ID = Threads 사용자 ID\n"
            "  THREADS_TOKEN   = 액세스 토큰\n"
            "Meta for Developers(developers.facebook.com)에서 발급하세요."
        )
    return user_id, token


def create_media_container(user_id: str, token: str, text: str, image_url: str | None = None) -> str:
    """미디어 컨테이너 생성 → container_id 반환."""
    params: dict = {
        "access_token": token,
        "text": text,
        "media_type": "IMAGE" if image_url else "TEXT",
    }
    if image_url:
        params["image_url"] = image_url

    res = requests.post(f"{THREADS_API}/{user_id}/threads", data=params, timeout=30)
    if not res.ok:
        logger.error("컨테이너 생성 실패: %s", res.text)
        res.raise_for_status()

    container_id = res.json()["id"]
    logger.info("컨테이너 생성 완료: %s", container_id)
    return container_id


def publish_container(user_id: str, token: str, container_id: str) -> str:
    """컨테이너 게시 → post_id 반환."""
    # Meta 권장: 컨테이너 생성 후 30초 대기
    time.sleep(30)

    res = requests.post(
        f"{THREADS_API}/{user_id}/threads_publish",
        data={"access_token": token, "creation_id": container_id},
        timeout=30,
    )
    if not res.ok:
        logger.error("게시 실패: %s", res.text)
        res.raise_for_status()

    post_id = res.json()["id"]
    logger.info("게시 완료: https://www.threads.net/post/%s", post_id)
    return post_id


def post_to_threads(caption: str, image_path: Path | None = None) -> str:
    """
    Threads에 포스팅.
    image_path 있으면 이미지 업로드 후 이미지 포스트.
    없으면 텍스트 전용 포스트.
    returns: post_id
    """
    user_id, token = _get_credentials()

    image_url = None
    if image_path and image_path.exists():
        image_url = upload_image_imgbb(image_path)

    container_id = create_media_container(user_id, token, caption, image_url)
    post_id = publish_container(user_id, token, container_id)
    return post_id


# ── 진입점 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # 카드 생성 후 포스팅
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from etl.sns_publisher.card_generator import run as generate

    print("카드 생성 중...")
    result = generate()
    caption = Path(result["caption"]).read_text(encoding="utf-8")
    image_path = Path(result["cover"])

    print(f"이미지: {image_path}")
    print(f"캡션 길이: {len(caption)}자")

    confirm = input("\nThreads에 게시하시겠습니까? (y/N): ").strip().lower()
    if confirm == "y":
        post_id = post_to_threads(caption, image_path)
        print(f"\n게시 완료: {post_id}")
    else:
        print("취소됨.")
