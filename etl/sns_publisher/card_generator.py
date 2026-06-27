"""
CAN SLIM 일일 TOP 종목 SNS 카드 이미지 생성기 (1080x1080)

출력:
  output/card_YYYYMMDD.png  — 인스타그램/쓰레드용 정사각형 카드
  output/caption_YYYYMMDD.txt — 텍스트 캡션
"""
import os
import textwrap
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import psycopg2

# ── 색상 팔레트 ──────────────────────────────────────────────────
BG        = (13, 17, 23)       # #0d1117
SURFACE   = (22, 27, 34)       # #161b22
BORDER    = (33, 38, 45)       # #21262d
ACCENT    = (31, 111, 235)     # #1f6feb (blue)
GREEN     = (74, 222, 128)     # #4ade80
YELLOW    = (250, 189, 68)     # #fabd44
RED       = (248, 113, 113)    # #f87171
TEXT_PRI  = (230, 237, 243)    # #e6edf3
TEXT_SEC  = (139, 148, 158)    # #8b949e
TEXT_DIM  = (75, 85, 99)       # #4b5563

SIZE      = 1080
PAD       = 54

# ── 폰트 로드 ────────────────────────────────────────────────────
def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """시스템 폰트에서 한글 지원 폰트 탐색."""
    candidates = [
        # Windows
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
        # Linux
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _score_color(score: float | None) -> tuple:
    if score is None: return TEXT_DIM
    if score >= 80:   return GREEN
    if score >= 65:   return (134, 239, 172)
    if score >= 50:   return YELLOW
    return RED


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)


def _draw_score_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, score: float | None):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=BORDER)
    if score:
        fill_w = int(w * min(score, 100) / 100)
        color = _score_color(score)
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=color)


# ── DB 조회 ──────────────────────────────────────────────────────
def fetch_top_stocks(n: int = 5) -> list[dict]:
    conn = psycopg2.connect(dbname="canslim", user="canslim_user", password="1234", host="localhost")
    cur = conn.cursor()
    cur.execute("""
        SELECT i.ticker, i.name, i.sector,
               cs.composite_score, cs.c_score, cs.a_score,
               cs.n_score, cs.s_score, cs.i_score, cs.m_score,
               cs.score_date,
               pd.close AS close_price,
               CASE WHEN pd_prev.close > 0
                    THEN (pd.close - pd_prev.close) / pd_prev.close * 100
                    ELSE NULL END AS change_rate,
               dm.market_cap_tril
        FROM canslim_scores cs
        JOIN (
            SELECT security_id, MAX(score_date) AS md
            FROM canslim_scores GROUP BY security_id
        ) latest ON cs.security_id = latest.security_id AND cs.score_date = latest.md
        JOIN instruments i ON i.id = cs.security_id
        LEFT JOIN price_daily pd ON pd.security_id = cs.security_id AND pd.trade_date = cs.score_date
        LEFT JOIN LATERAL (
            SELECT close FROM price_daily
            WHERE security_id = cs.security_id AND trade_date < cs.score_date
            ORDER BY trade_date DESC LIMIT 1
        ) pd_prev ON TRUE
        LEFT JOIN LATERAL (
            SELECT market_cap_tril FROM derived_metrics
            WHERE security_id = cs.security_id AND as_of_date <= cs.score_date
            ORDER BY as_of_date DESC LIMIT 1
        ) dm ON TRUE
        WHERE cs.composite_score IS NOT NULL
        ORDER BY cs.composite_score DESC
        LIMIT %s
    """, (n,))
    cols = ["ticker", "name", "sector", "composite", "c", "a", "n", "s", "i", "m",
            "score_date", "close_price", "change_rate", "market_cap"]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


# ── 카드 생성 ────────────────────────────────────────────────────
def generate_card(stocks: list[dict], output_path: Path) -> Path:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    font_title  = _load_font(36, bold=True)
    font_sub    = _load_font(22)
    font_label  = _load_font(19)
    font_small  = _load_font(16)
    font_score  = _load_font(44, bold=True)
    font_ticker = _load_font(20, bold=True)
    font_name   = _load_font(26, bold=True)
    font_rank   = _load_font(32, bold=True)

    today = stocks[0]["score_date"] if stocks else date.today()
    date_str = today.strftime("%Y.%m.%d") if hasattr(today, "strftime") else str(today)

    # ── 헤더 ──
    header_h = 120
    _draw_rounded_rect(draw, [0, 0, SIZE, header_h + 20], radius=0, fill=SURFACE)
    draw.line([(0, header_h), (SIZE, header_h)], fill=BORDER, width=1)

    # 브랜드
    draw.text((PAD, 28), "CANSLIM", font=font_title, fill=ACCENT)
    draw.text((PAD, 68), "성장주 레이더", font=font_sub, fill=TEXT_SEC)
    # 날짜
    date_w = draw.textlength(date_str, font=font_sub)
    draw.text((SIZE - PAD - date_w, 28), date_str, font=font_sub, fill=TEXT_SEC)
    draw.text((SIZE - PAD - 110, 58), "오늘의 TOP 5", font=font_small, fill=TEXT_DIM)

    # ── 종목 카드 ──
    card_top   = header_h + 24
    card_h     = 155
    card_gap   = 12
    card_w     = SIZE - PAD * 2

    for idx, s in enumerate(stocks[:5]):
        cy = card_top + idx * (card_h + card_gap)
        cx = PAD

        # 카드 배경
        _draw_rounded_rect(draw, [cx, cy, cx + card_w, cy + card_h], radius=14, fill=SURFACE, outline=BORDER, width=1)

        # 순위 뱃지
        rank_x, rank_y = cx + 18, cy + card_h // 2 - 22
        rank_txt = f"#{idx + 1}"
        rcolor = [GREEN, (134,239,172), YELLOW, (249,115,22), RED][idx]
        draw.text((rank_x, rank_y), rank_txt, font=font_rank, fill=rcolor)

        # 종목명 + 티커
        name_x = rank_x + 72
        name = s["name"][:10]
        draw.text((name_x, cy + 22), name, font=font_name, fill=TEXT_PRI)
        draw.text((name_x, cy + 56), s["ticker"], font=font_ticker, fill=ACCENT)
        if s["sector"]:
            sector = s["sector"][:8]
            draw.text((name_x, cy + 84), sector, font=font_small, fill=TEXT_DIM)

        # 종합 점수 (우측)
        comp = float(s["composite"] or 0)
        score_txt = f"{comp:.1f}"
        sw = draw.textlength(score_txt, font=font_score)
        score_x = cx + card_w - 80 - sw
        draw.text((score_x, cy + 18), score_txt, font=font_score, fill=_score_color(comp))
        draw.text((score_x, cy + 72), "종합점수", font=font_small, fill=TEXT_DIM)

        # 개별 팩터 바 (하단)
        bar_y   = cy + card_h - 36
        bar_h   = 6
        factors = [("C", s["c"]), ("A", s["a"]), ("N", s["n"]),
                   ("S", s["s"]), ("I", s["i"]), ("M", s["m"])]
        bar_total_w = card_w - 80 - 20
        seg_w = bar_total_w // len(factors)
        bx = name_x
        for label, val in factors:
            v = float(val) if val is not None else None
            draw.text((bx, bar_y - 16), label, font=font_small, fill=TEXT_DIM)
            _draw_score_bar(draw, bx, bar_y, seg_w - 6, bar_h, v)
            bx += seg_w

        # 등락률 (있으면)
        if s["change_rate"] is not None:
            cr = float(s["change_rate"])
            cr_txt = f"{'+' if cr >= 0 else ''}{cr:.2f}%"
            cr_color = GREEN if cr > 0 else RED if cr < 0 else TEXT_SEC
            cr_w = draw.textlength(cr_txt, font=font_label)
            draw.text((cx + card_w - cr_w - 12, cy + card_h - 30), cr_txt, font=font_label, fill=cr_color)

    # ── 푸터 ──
    footer_y = card_top + 5 * (card_h + card_gap) + 8
    draw.line([(PAD, footer_y), (SIZE - PAD, footer_y)], fill=BORDER, width=1)
    draw.text((PAD, footer_y + 10), "본 내용은 투자 참고용이며 투자 손실에 대한 책임은 투자자에게 있습니다.",
              font=font_small, fill=TEXT_DIM)
    draw.text((SIZE - PAD - 180, footer_y + 10), "#CANSLIM #성장주 #주식스크리너", font=font_small, fill=TEXT_DIM)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    return output_path


# ── 캡션 생성 ────────────────────────────────────────────────────
def generate_caption(stocks: list[dict]) -> str:
    today = stocks[0]["score_date"] if stocks else date.today()
    date_str = today.strftime("%Y년 %m월 %d일") if hasattr(today, "strftime") else str(today)

    lines = [
        f"📊 {date_str} CAN SLIM 성장주 TOP 5",
        "",
        "월가의 전설 윌리엄 오닐의 7대 기준으로 선별한 오늘의 주도주입니다.",
        "",
    ]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, s in enumerate(stocks[:5]):
        comp = float(s["composite"] or 0)
        cr   = float(s["change_rate"] or 0) if s["change_rate"] is not None else None
        cr_txt = f" ({'+' if cr and cr >= 0 else ''}{cr:.1f}%)" if cr is not None else ""
        lines.append(f"{medals[idx]} {s['name']}({s['ticker']}){cr_txt}")
        lines.append(f"   종합 {comp:.1f}점  C:{_fmt(s['c'])} A:{_fmt(s['a'])} N:{_fmt(s['n'])} S:{_fmt(s['s'])} I:{_fmt(s['i'])}")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        "🔎 지표 설명",
        "C — 분기 EPS 성장  A — 연간 성장",
        "N — 신고가 근접    S — 수급 강도",
        "I — 기관 참여      M — 시장 방향",
        "",
        "⚠️ 투자 참고용 정보입니다. 투자 결정과 손익 책임은 투자자 본인에게 있습니다.",
        "",
        "#CANSLIM #성장주 #주식스크리너 #한국주식 #주식공부 #종목추천아님",
    ]
    return "\n".join(lines)


def _fmt(v) -> str:
    return f"{float(v):.0f}" if v is not None else "-"


# ── 진입점 ───────────────────────────────────────────────────────
def run(n: int = 5, out_dir: str = "output/sns") -> dict:
    stocks = fetch_top_stocks(n)
    if not stocks:
        raise RuntimeError("DB에서 종목 조회 실패")

    today_str = datetime.now().strftime("%Y%m%d")
    out = Path(out_dir)

    img_path = out / f"card_{today_str}.png"
    cap_path = out / f"caption_{today_str}.txt"

    generate_card(stocks, img_path)
    caption = generate_caption(stocks)
    cap_path.write_text(caption, encoding="utf-8")

    return {"image": str(img_path), "caption": str(cap_path), "stocks": stocks}


if __name__ == "__main__":
    import logging, os
    os.environ.setdefault("PYTHONUTF8", "1")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    result = run()
    print(f"\n이미지 생성: {result['image']}")
    print(f"캡션 생성:   {result['caption']}")
    print("\n─── 캡션 미리보기 ─────────────────────────────")
    print(Path(result['caption']).read_text(encoding="utf-8"))
