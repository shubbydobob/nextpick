"""
SNS 통합 CLI — 카드 생성, 블로그 포스트 생성 및 포스팅

사용법:
  python -m etl.sns_publisher.run_sns [--threads] [--instagram] [--blog] [--youtube] [--dry-run]

옵션:
  --dry-run        카드/캡션 생성 후 미리보기만 출력 (기본값)
  --threads        Threads에 게시
  --instagram      Instagram에 게시
  --blog           블로그 포스트 생성 (MD + HTML)
  --youtube        유튜브 쇼츠 생성 및 업로드
  --n N            TOP N 종목 카드 (기본: 5)
  --out DIR        SNS 카드 출력 디렉터리 (기본: output/sns)
  --blog-out DIR   블로그 출력 디렉터리 (기본: output/blog)
  --shorts-out DIR 쇼츠 출력 디렉터리 (기본: output/shorts)

예시:
  python -m etl.sns_publisher.run_sns                                          # dry-run
  python -m etl.sns_publisher.run_sns --threads                                # Threads만
  python -m etl.sns_publisher.run_sns --threads --instagram --blog --youtube   # 전체
"""
import argparse
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="CAN SLIM SNS 포스팅 CLI")
    parser.add_argument("--threads",    action="store_true", help="Threads에 게시")
    parser.add_argument("--instagram",  action="store_true", help="Instagram에 게시")
    parser.add_argument("--blog",       action="store_true", help="블로그 포스트 생성 (MD + HTML)")
    parser.add_argument("--youtube",    action="store_true", help="유튜브 쇼츠 생성 및 업로드")
    parser.add_argument("--dry-run",    action="store_true", help="미리보기만 (기본값, 포스팅 안 함)")
    parser.add_argument("--n",          type=int, default=5,               help="TOP N 종목 (기본: 5)")
    parser.add_argument("--out",        type=str, default="output/sns",    help="SNS 카드 출력 디렉터리")
    parser.add_argument("--blog-out",   type=str, default="output/blog",   help="블로그 출력 디렉터리")
    parser.add_argument("--shorts-out", type=str, default="output/shorts", help="쇼츠 출력 디렉터리")
    args = parser.parse_args()

    # 아무 플래그도 없으면 dry-run
    if not args.threads and not args.instagram:
        args.dry_run = True

    # ── 1. 카드 생성 ────────────────────────────────────────────
    logger.info("카드 생성 시작 (TOP %d)", args.n)
    from etl.sns_publisher.card_generator import run as generate_card
    result = generate_card(n=args.n, out_dir=args.out)

    image_path = Path(result["cover"])
    caption_path = Path(result["caption"])
    caption = caption_path.read_text(encoding="utf-8")

    logger.info("이미지: %s", image_path)
    logger.info("캡션: %s", caption_path)

    # ── 2. 미리보기 출력 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("캡션 미리보기")
    print("=" * 60)
    print(caption)
    print("=" * 60)

    if args.dry_run and not args.blog:
        print("\n[dry-run] 포스팅 건너뜀. --threads 또는 --instagram 플래그로 실제 게시하세요.")
        return

    # ── 3. Threads 게시 ─────────────────────────────────────────
    if args.threads:
        logger.info("Threads 게시 시작...")
        try:
            from etl.sns_publisher.threads_poster import post_to_threads
            post_id = post_to_threads(caption, image_path)
            logger.info("Threads 게시 완료: post_id=%s", post_id)
            print(f"\n[Threads] 게시 완료: {post_id}")
        except RuntimeError as e:
            logger.error("Threads 게시 실패: %s", e)
            print(f"\n[Threads] 오류: {e}")
        except Exception as e:
            logger.error("Threads 게시 중 예외: %s", e)
            print(f"\n[Threads] 예외: {e}")

    # ── 4. Instagram 게시 ────────────────────────────────────────
    if args.instagram:
        logger.info("Instagram 게시 시작...")
        try:
            from etl.sns_publisher.instagram_poster import post_to_instagram
            media_id = post_to_instagram(caption, image_path)
            logger.info("Instagram 게시 완료: media_id=%s", media_id)
            print(f"\n[Instagram] 게시 완료: media_id={media_id}")
        except RuntimeError as e:
            logger.error("Instagram 게시 실패: %s", e)
            print(f"\n[Instagram] 오류: {e}")
        except Exception as e:
            logger.error("Instagram 게시 중 예외: %s", e)
            print(f"\n[Instagram] 예외: {e}")

    # ── 5. 유튜브 쇼츠 생성 + 업로드 ───────────────────────────
    if args.youtube:
        logger.info("유튜브 쇼츠 생성 시작...")
        try:
            from etl.sns_publisher.shorts_generator import run as generate_shorts
            shorts = generate_shorts(n=args.n, sns_dir=args.out, out_dir=args.shorts_out)
            logger.info("쇼츠 영상 생성 완료: %s (%.1fs)", shorts["video"], shorts["duration"])
            print(f"\n[YouTube] 영상: {shorts['video']}  ({shorts['duration']:.1f}s)")

            from etl.sns_publisher.youtube_uploader import post_to_youtube
            from pathlib import Path as _Path
            video_id = post_to_youtube(
                _Path(shorts["video"]),
                shorts["stocks"],
                shorts["stocks"][0]["score_date"],
            )
            print(f"[YouTube] 업로드 완료: https://youtu.be/{video_id}")
        except RuntimeError as e:
            logger.error("유튜브 업로드 실패: %s", e)
            print(f"\n[YouTube] 오류: {e}")
        except Exception as e:
            logger.error("유튜브 처리 중 예외: %s", e)
            print(f"\n[YouTube] 예외: {e}")

    # ── 6. 블로그 포스트 생성 ────────────────────────────────────
    if args.blog:
        logger.info("블로그 포스트 생성 시작...")
        try:
            from etl.sns_publisher.blog_generator import run as generate_blog
            blog = generate_blog(n=args.n, out_dir=args.blog_out)
            logger.info("블로그 생성 완료")
            print(f"\n[Blog] 마크다운: {blog['markdown']}")
            print(f"[Blog] HTML:     {blog['html']}")
        except Exception as e:
            logger.error("블로그 생성 실패: %s", e)
            print(f"\n[Blog] 오류: {e}")


if __name__ == "__main__":
    main()
