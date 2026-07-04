"""
CAN SLIM 유튜브 쇼츠 자동 생성기

구성:
  인트로 (3s)  → TOP 5 종목 슬라이드 각 8s → 아웃트로 (3s)
  총 ~46s, 1080×1920 세로 MP4

의존성:
  pip install moviepy edge-tts

출력:
  output/shorts/shorts_YYYYMMDD.mp4
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

# ── 쇼츠 포맷 ──────────────────────────────────────────────────────
W, H     = 1080, 1920   # 세로
CARD_W   = 1080         # 카드 원본 너비 (1080×1080)
CARD_Y   = (H - CARD_W) // 2   # 카드 Y 오프셋 (중앙 배치)

FPS      = 30
INTRO_S  = 3
STOCK_S  = 8
OUTRO_S  = 3

BG       = (12, 14, 20)
ACC      = (99, 179, 237)
PRI      = (245, 248, 255)
SEC      = (130, 145, 175)
DIM      = (58, 68, 92)
GREEN    = (52, 211, 153)
RANK_C   = [GREEN, (110, 231, 183), (251, 191, 36), (251, 146, 60), (248, 113, 113)]


# ── 폰트 ───────────────────────────────────────────────────────────
def _F(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in [
        f"C:/Windows/Fonts/{'malgunbd' if bold else 'malgun'}.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        f"/usr/share/fonts/truetype/nanum/NanumGothic{'Bold' if bold else ''}.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ── 유틸 ───────────────────────────────────────────────────────────
def _fmt(v) -> str:
    return f"{float(v):.0f}" if v is not None else "—"

def _pct(v) -> str:
    if v is None: return "—"
    v = float(v); s = "+" if v >= 0 else ""; return f"{s}{v:.1f}%"


# ── 인트로 프레임 ──────────────────────────────────────────────────
def _make_intro_frame(score_date) -> Image.Image:
    ds = score_date.strftime("%Y.%m.%d") if hasattr(score_date, "strftime") else str(score_date)
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 8], fill=ACC)

    cy = H // 2 - 160
    d.text((W // 2, cy),       "CAN SLIM",      font=_F(56, True),  fill=ACC,  anchor="mm")
    d.text((W // 2, cy + 80),  "성장주 레이더",  font=_F(38),        fill=SEC,  anchor="mm")
    d.text((W // 2, cy + 180), "오늘의",         font=_F(52),        fill=SEC,  anchor="mm")
    d.text((W // 2, cy + 260), "TOP 5",          font=_F(160, True), fill=PRI,  anchor="mm")
    d.text((W // 2, cy + 400), "성장주",         font=_F(52),        fill=SEC,  anchor="mm")
    d.text((W // 2, cy + 480), ds,               font=_F(32),        fill=DIM,  anchor="mm")

    d.rectangle([0, H - 8, W, H], fill=ACC)
    return img


# ── 종목 슬라이드 프레임 (카드 이미지 위아래 패딩) ──────────────────
def _make_stock_frame(card_path: Path, rank: int, s: dict) -> Image.Image:
    img   = Image.new("RGB", (W, H), BG)
    d     = ImageDraw.Draw(img)
    rc    = RANK_C[min(rank - 1, 4)]
    comp  = float(s["composite"] or 0)

    # 상단 포인트 바
    d.rectangle([0, 0, W, 8], fill=rc)

    # 상단 정보 영역 (카드 위)
    top_h = CARD_Y
    d.text((54, top_h // 2 - 30), f"#{rank}  {s['name']}", font=_F(48, True), fill=PRI)
    d.text((54, top_h // 2 + 30), s.get("sector") or "",   font=_F(28),        fill=SEC)

    sc_t  = f"{comp:.0f}점"
    sc_w  = d.textlength(sc_t, font=_F(64, True))
    d.text((W - 54 - sc_w, top_h // 2 - 36), sc_t, font=_F(64, True), fill=rc)

    # 카드 이미지 붙이기
    if card_path.exists():
        card = Image.open(card_path).convert("RGB")
        if card.width != CARD_W:
            card = card.resize((CARD_W, CARD_W), Image.LANCZOS)
        img.paste(card, (0, CARD_Y))
    else:
        d.rectangle([0, CARD_Y, W, CARD_Y + CARD_W], fill=(20, 24, 34))
        d.text((W // 2, CARD_Y + CARD_W // 2), "카드 없음", font=_F(40), fill=DIM, anchor="mm")

    # 하단 정보 (카드 아래)
    bot_y = CARD_Y + CARD_W + 20
    kpis  = [
        ("C 분기성장", _fmt(s["c"])),
        ("L 상대강도", _fmt(s["l"])),
        ("S 수급강도", _fmt(s["s"])),
    ]
    kw = (W - 108) // 3
    for i, (lbl, val) in enumerate(kpis):
        kx = 54 + i * kw
        d.text((kx + kw // 2, bot_y + 10), lbl, font=_F(24),        fill=SEC, anchor="mm")
        d.text((kx + kw // 2, bot_y + 52), val, font=_F(44, True),   fill=rc,  anchor="mm")

    # 하단 면책
    d.rectangle([0, H - 8, W, H], fill=rc)
    d.text((W // 2, H - 38), "⚠ 투자 참고용 · 손실 책임은 투자자에게 있습니다.",
           font=_F(20), fill=DIM, anchor="mm")
    return img


# ── 아웃트로 프레임 ────────────────────────────────────────────────
def _make_outro_frame() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=ACC)
    cy  = H // 2
    d.text((W // 2, cy - 80), "더 자세한 정보는",        font=_F(38),       fill=SEC, anchor="mm")
    d.text((W // 2, cy),      "성장주스크리너",           font=_F(72, True), fill=PRI, anchor="mm")
    d.text((W // 2, cy + 80), "k-stock-score.vercel.app", font=_F(30),      fill=ACC, anchor="mm")
    d.text((W // 2, cy + 160), "#CANSLIM #성장주 #주식",  font=_F(28),      fill=DIM, anchor="mm")
    d.rectangle([0, H - 8, W, H], fill=ACC)
    return img


# ── TTS 스크립트 ───────────────────────────────────────────────────
def _tts_script_intro(stocks: list[dict], score_date) -> str:
    ds = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    names = ", ".join(s["name"] for s in stocks[:5])
    return f"{ds} CAN SLIM TOP 5 성장주를 소개합니다. {names}입니다."


def _tts_script_stock(s: dict, rank: int) -> str:
    comp = float(s["composite"] or 0)
    c_t  = f"분기 EPS 점수 {_fmt(s['c'])}점" if s["c"] else ""
    l_t  = f"상대강도 {_fmt(s['l'])}점" if s["l"] else ""
    yoy  = f"전년 대비 EPS {_pct(s.get('yoy'))} 성장" if s.get("yoy") else ""
    parts = [p for p in [c_t, l_t, yoy] if p]
    detail = ", ".join(parts) if parts else "상세 데이터를 확인하세요"
    return (
        f"{rank}위 {s['name']}. "
        f"종합 점수 {comp:.0f}점. "
        f"{detail}."
    )


def _tts_script_outro() -> str:
    return "더 자세한 종목 분석은 성장주스크리너에서 확인하세요. 구독과 좋아요 부탁드립니다."


# ── edge-tts 비동기 생성 ───────────────────────────────────────────
async def _tts_async(scripts: list[str], out_dir: Path) -> list[Path]:
    import edge_tts
    voice  = "ko-KR-SunHiNeural"
    paths  = []
    for i, text in enumerate(scripts):
        out = out_dir / f"tts_{i}.mp3"
        comm = edge_tts.Communicate(text, voice)
        await comm.save(str(out))
        logger.info("TTS [%d/%d] 생성: %s", i + 1, len(scripts), out.name)
        paths.append(out)
    return paths


def _generate_tts(scripts: list[str], out_dir: Path) -> list[Path]:
    return asyncio.run(_tts_async(scripts, out_dir))


# ── 영상 조립 (moviepy) ────────────────────────────────────────────
def _build_video(
    frames: list[Image.Image],
    audio_paths: list[Path],
    durations: list[float],
    out_path: Path,
) -> None:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    import numpy as np

    clips = []
    for frame, audio_p, dur in zip(frames, audio_paths, durations):
        arr  = np.array(frame)
        if audio_p and audio_p.exists():
            audio = AudioFileClip(str(audio_p))
            clip_dur = max(audio.duration + 0.5, dur)
            clip = ImageClip(arr, duration=clip_dur).with_fps(FPS).with_audio(audio)
        else:
            clip = ImageClip(arr, duration=dur).with_fps(FPS)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    logger.info("영상 저장 완료: %s (%.1fs)", out_path, final.duration)


# ── 진입점 ────────────────────────────────────────────────────────
def run(n: int = 5, sns_dir: str = "output/sns", out_dir: str = "output/shorts") -> dict:
    """
    쇼츠 영상 생성.
    sns_dir: card_generator 출력 디렉터리 (커버·상세 카드 PNG 있어야 함)
    out_dir: MP4 출력 디렉터리
    """
    from etl.sns_publisher.card_generator import fetch
    stocks = fetch(n)
    if not stocks:
        raise RuntimeError("DB 조회 실패")

    score_date = stocks[0]["score_date"]
    ts  = score_date.strftime("%Y%m%d") if hasattr(score_date, "strftime") else datetime.now().strftime("%Y%m%d")
    sns = Path(sns_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── 1. 프레임 생성 ──────────────────────────────────────────
    logger.info("프레임 생성 중...")
    frames: list[Image.Image] = [_make_intro_frame(score_date)]
    for rank, s in enumerate(stocks[:n], 1):
        card_path = sns / f"detail_{ts}_{s['ticker']}.png"
        frames.append(_make_stock_frame(card_path, rank, s))
    frames.append(_make_outro_frame())

    # ── 2. TTS 스크립트 ─────────────────────────────────────────
    logger.info("TTS 생성 중...")
    scripts = [_tts_script_intro(stocks, score_date)]
    for rank, s in enumerate(stocks[:n], 1):
        scripts.append(_tts_script_stock(s, rank))
    scripts.append(_tts_script_outro())

    with tempfile.TemporaryDirectory() as tmp:
        audio_paths = _generate_tts(scripts, Path(tmp))

        # ── 3. 슬라이드 길이: TTS 길이 기준, 최소값 보장 ──────
        from moviepy import AudioFileClip
        min_durs = [INTRO_S] + [STOCK_S] * n + [OUTRO_S]
        durations = []
        for ap, md in zip(audio_paths, min_durs):
            if ap.exists():
                adur = AudioFileClip(str(ap)).duration
                durations.append(max(adur + 0.5, float(md)))
            else:
                durations.append(float(md))

        # ── 4. 영상 조립 ───────────────────────────────────────
        logger.info("영상 조립 중 (총 %.1fs)...", sum(durations))
        out_path = out / f"shorts_{ts}.mp4"
        _build_video(frames, audio_paths, durations, out_path)

    return {"video": str(out_path), "duration": sum(durations), "stocks": stocks}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run()
    print(f"영상: {result['video']}  ({result['duration']:.1f}s)")
