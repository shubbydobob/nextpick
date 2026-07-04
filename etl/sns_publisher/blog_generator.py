"""
CAN SLIM 블로그 포스트 자동 생성기

출력:
  blog_{YYYYMMDD}.md   — 마크다운 (티스토리/벨로그)
  blog_{YYYYMMDD}.html — HTML (네이버 블로그)

사용법:
  python -m etl.sns_publisher.blog_generator
  python -m etl.sns_publisher.blog_generator --n 5 --out output/blog
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from textwrap import dedent


# ── 유틸 (card_generator와 동일 규칙) ───────────────────────────────
def _fmt(v) -> str:
    return f"{float(v):.0f}" if v is not None else "—"

def _pct(v, plus=True) -> str:
    if v is None:
        return "—"
    v = float(v)
    s = "+" if v >= 0 and plus else ""
    return f"{s}{v:.1f}%"

def _price(v) -> str:
    return f"{int(v):,}원" if v else "—"

def _cap(v) -> str:
    if v is None:
        return "—"
    v = float(v)
    return f"{v:.1f}조" if v >= 1 else f"{v * 1000:.0f}억"

def _buy(v) -> str:
    if v is None:
        return "—"
    v = int(v)
    s = "+" if v >= 0 else "-"
    a = abs(v)
    if a >= 1_000_000:
        return f"{s}{a / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{s}{a // 1_000}K"
    return f"{s}{a}"

def _score_label(v) -> str:
    if v is None:
        return "데이터 없음"
    v = float(v)
    if v >= 80: return "매우 강함"
    if v >= 60: return "강함"
    if v >= 45: return "보통"
    if v >= 30: return "약함"
    return "매우 약함"


# ── 마크다운 생성 ────────────────────────────────────────────────────
def generate_markdown(stocks: list[dict], score_date) -> str:
    ds = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    ds_compact = score_date.strftime("%Y.%m.%d") if hasattr(score_date, "strftime") else str(score_date)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    lines: list[str] = []

    # ── 제목 & 서문 ──
    lines += [
        f"# {ds} CAN SLIM 성장주 TOP {len(stocks)} 분석",
        "",
        f"> **{ds_compact}** 기준으로 CAN SLIM 7대 요소를 종합 스코어링한 결과입니다.",
        "> 윌리엄 오닐의 방법론을 기반으로 분기 EPS 성장, 연간 성장성, 신고가 근접도,",
        "> 수급 강도, 상대강도, 기관 참여, 시장 방향을 정량화했습니다.",
        "",
        "---",
        "",
    ]

    # ── 요약 테이블 ──
    lines += [
        "## 📊 TOP 5 종합 순위",
        "",
        "| 순위 | 종목 | 티커 | 섹터 | 종합점수 | C | A | N | S | L | I | M |",
        "|:---:|------|------|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for i, s in enumerate(stocks):
        lines.append(
            f"| {medals[i]} | **{s['name']}** | {s['ticker']} | {s.get('sector') or '—'} "
            f"| **{_fmt(s['composite'])}** "
            f"| {_fmt(s['c'])} | {_fmt(s['a'])} | {_fmt(s['n'])} "
            f"| {_fmt(s['s'])} | {_fmt(s['l'])} | {_fmt(s['i'])} | {_fmt(s['m'])} |"
        )
    lines += ["", "---", ""]

    # ── CANSLIM 요소 설명 ──
    lines += [
        "## 📖 CAN SLIM 7대 요소란?",
        "",
        "| 요소 | 의미 | 판단 기준 |",
        "|:---:|------|----------|",
        "| **C** | 분기 EPS 성장 (Current Quarterly Earnings) | 전년 동기 대비 +25% 이상 |",
        "| **A** | 연간 EPS 성장 (Annual Earnings Growth) | 최근 3년 연평균 +25% 이상 |",
        "| **N** | 신제품·신고가 (New Products / New Highs) | 52주 고점 대비 -15% 이내 |",
        "| **S** | 수급 (Supply & Demand) | 기관·외인 순매수 강도 |",
        "| **L** | 주도주 (Leader or Laggard) | RS 백분위 80위 이상 |",
        "| **I** | 기관 매집 (Institutional Sponsorship) | 기관 보유 트렌드 증가 |",
        "| **M** | 시장 방향 (Market Direction) | Follow-through Day 여부 |",
        "",
        "---",
        "",
    ]

    # ── 종목별 상세 ──
    lines.append("## 🔍 종목별 상세 분석")
    lines.append("")

    for i, s in enumerate(stocks):
        comp = float(s["composite"] or 0)
        cr   = float(s["cr"]) if s["cr"] is not None else None
        cr_t = f" ({_pct(cr)})" if cr is not None else ""

        lines += [
            f"### {medals[i]} {i+1}위 — {s['name']} ({s['ticker']})",
            "",
            f"- **시장**: {s['market']}  |  **섹터**: {s.get('sector') or '—'}",
            f"- **현재가**: {_price(s['close'])}{cr_t}  |  **시가총액**: {_cap(s['cap'])}",
            f"- **종합 점수**: {comp:.0f}점 ({_score_label(comp)})",
            "",
            "#### CANSLIM 팩터 분석",
            "",
            "| 팩터 | 점수 | 평가 | 세부 수치 |",
            "|:---:|:---:|------|----------|",
            f"| **C** 분기 EPS 성장 | {_fmt(s['c'])} | {_score_label(s['c'])} | YoY {_pct(s['yoy'])} |",
            f"| **A** 연간 성장성   | {_fmt(s['a'])} | {_score_label(s['a'])} | 3yr CAGR {_pct(s['cagr'], True)} |",
            f"| **N** 신고가 근접   | {_fmt(s['n'])} | {_score_label(s['n'])} | 고점 대비 {_pct(s['h52'])} |",
            f"| **S** 수급 강도     | {_fmt(s['s'])} | {_score_label(s['s'])} | 기관 {_buy(s['inst'])} / 외인 {_buy(s['foreign'])} |",
            f"| **L** 상대 강도     | {_fmt(s['l'])} | {_score_label(s['l'])} | RS 백분위 {_fmt(s['rs'])}위 |",
            f"| **I** 기관 참여     | {_fmt(s['i'])} | {_score_label(s['i'])} | 기관 트렌드 |",
            f"| **M** 시장 방향     | {_fmt(s['m'])} | {_score_label(s['m'])} | 시장 국면 |",
            "",
        ]

        if i < len(stocks) - 1:
            lines.append("---")
            lines.append("")

    # ── 마무리 ──
    lines += [
        "---",
        "",
        "## ⚠️ 투자 유의사항",
        "",
        "본 분석은 CAN SLIM 방법론에 따른 **참고용 정보**입니다.",
        "투자 판단 및 그에 따른 손익은 전적으로 투자자 본인에게 귀속됩니다.",
        "과거 성과가 미래 수익을 보장하지 않습니다.",
        "",
        f"*자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | CAN SLIM 스코어링 엔진*",
        "",
        "**태그**: #CANSLIM #성장주 #주식스크리너 #한국주식 #주식공부 #오닐투자법",
    ]

    return "\n".join(lines)


# ── HTML 생성 (네이버 블로그용) ──────────────────────────────────────
def generate_html(stocks: list[dict], score_date) -> str:
    ds = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    def score_color(v) -> str:
        if v is None: return "#8899aa"
        v = float(v)
        if v >= 80: return "#34d399"
        if v >= 60: return "#6ee7b7"
        if v >= 45: return "#fbbf24"
        if v >= 30: return "#fb923c"
        return "#f87171"

    # 요약 테이블 rows
    table_rows = ""
    for i, s in enumerate(stocks):
        comp = float(s["composite"] or 0)
        c_c  = score_color(comp)
        table_rows += dedent(f"""
            <tr>
              <td style="text-align:center;font-size:20px">{medals[i]}</td>
              <td><strong>{s['name']}</strong><br><span style="color:#888;font-size:12px">{s['ticker']} · {s.get('sector') or '—'}</span></td>
              <td style="text-align:center;color:{c_c};font-weight:bold;font-size:18px">{_fmt(comp)}</td>
              <td style="text-align:center;color:{score_color(s['c'])}">{_fmt(s['c'])}</td>
              <td style="text-align:center;color:{score_color(s['a'])}">{_fmt(s['a'])}</td>
              <td style="text-align:center;color:{score_color(s['n'])}">{_fmt(s['n'])}</td>
              <td style="text-align:center;color:{score_color(s['s'])}">{_fmt(s['s'])}</td>
              <td style="text-align:center;color:{score_color(s['l'])}">{_fmt(s['l'])}</td>
              <td style="text-align:center;color:{score_color(s['i'])}">{_fmt(s['i'])}</td>
              <td style="text-align:center;color:{score_color(s['m'])}">{_fmt(s['m'])}</td>
            </tr>
        """)

    # 종목별 상세 카드
    detail_cards = ""
    for i, s in enumerate(stocks):
        comp = float(s["composite"] or 0)
        cr   = float(s["cr"]) if s["cr"] is not None else None
        cr_style = f"color:{'#34d399' if (cr or 0) > 0 else '#f87171'}"
        cr_t     = f" <span style='{cr_style}'>({_pct(cr)})</span>" if cr is not None else ""
        c_c      = score_color(comp)

        factors = [
            ("C", "분기 EPS 성장", s["c"], f"YoY {_pct(s['yoy'])}"),
            ("A", "연간 성장성",   s["a"], f"3yr CAGR {_pct(s['cagr'], True)}"),
            ("N", "신고가 근접",   s["n"], f"고점 대비 {_pct(s['h52'])}"),
            ("S", "수급 강도",     s["s"], f"기관 {_buy(s['inst'])} / 외인 {_buy(s['foreign'])}"),
            ("L", "상대 강도",     s["l"], f"RS 백분위 {_fmt(s['rs'])}위"),
            ("I", "기관 참여",     s["i"], "기관 트렌드"),
            ("M", "시장 방향",     s["m"], "시장 국면"),
        ]

        factor_rows = ""
        for lbl, sub, score, detail_txt in factors:
            sc = score_color(score)
            bar_w = max(4, int(float(score) if score else 0))
            factor_rows += dedent(f"""
                <tr style="border-bottom:1px solid #1e2436">
                  <td style="padding:10px 8px;color:{sc};font-weight:bold;font-size:16px;width:32px">{lbl}</td>
                  <td style="padding:10px 8px">
                    <div style="font-weight:bold;color:#f0f4ff">{sub}</div>
                    <div style="color:#8899aa;font-size:12px">{detail_txt}</div>
                  </td>
                  <td style="padding:10px 8px;text-align:right;color:{sc};font-weight:bold;font-size:18px;width:52px">{_fmt(score)}</td>
                  <td style="padding:10px 8px;width:120px">
                    <div style="background:#1e2436;border-radius:4px;height:6px;overflow:hidden">
                      <div style="background:{sc};width:{bar_w}%;height:100%;border-radius:4px"></div>
                    </div>
                  </td>
                </tr>
            """)

        detail_cards += dedent(f"""
            <div style="background:#141824;border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid #1e2a40">
              <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px">
                <span style="font-size:28px">{medals[i]}</span>
                <span style="font-size:24px;font-weight:bold;color:#f0f4ff">{s['name']}</span>
                <span style="font-size:14px;color:#8899aa">{s['ticker']} · {s['market']}</span>
                <span style="margin-left:auto;font-size:36px;font-weight:bold;color:{c_c}">{_fmt(comp)}<span style="font-size:16px;color:#8899aa"> 점</span></span>
              </div>
              <div style="color:#8899aa;font-size:13px;margin-bottom:16px">{s.get('sector') or '—'}</div>
              <div style="font-size:22px;font-weight:bold;color:#f0f4ff;margin-bottom:4px">
                {_price(s['close'])}{cr_t}
              </div>
              <div style="color:#8899aa;font-size:13px;margin-bottom:20px">시가총액 {_cap(s['cap'])}</div>
              <table style="width:100%;border-collapse:collapse">
                {factor_rows}
              </table>
            </div>
        """)

    html = dedent(f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{ds} CAN SLIM 성장주 TOP {len(stocks)} 분석</title>
        </head>
        <body style="margin:0;padding:20px;background:#0c0f18;color:#f0f4ff;font-family:'Malgun Gothic',sans-serif;max-width:800px;margin:0 auto">

          <!-- 헤더 -->
          <div style="border-top:4px solid #63b3ed;padding-top:24px;margin-bottom:32px">
            <div style="color:#63b3ed;font-size:14px;font-weight:bold;letter-spacing:2px">CAN SLIM 성장주 레이더</div>
            <h1 style="margin:8px 0 4px;font-size:32px;color:#f0f4ff">{ds}<br>TOP {len(stocks)} 성장주 분석</h1>
            <p style="color:#8899aa;font-size:14px;margin:0">윌리엄 오닐의 7대 기준으로 선별한 오늘의 주도주</p>
          </div>

          <!-- 요약 테이블 -->
          <h2 style="color:#63b3ed;font-size:18px;margin-bottom:12px">📊 종합 순위</h2>
          <div style="overflow-x:auto;margin-bottom:32px">
            <table style="width:100%;border-collapse:collapse;font-size:13px">
              <thead>
                <tr style="background:#141824;color:#8899aa">
                  <th style="padding:10px 6px;text-align:center">#</th>
                  <th style="padding:10px 6px;text-align:left">종목</th>
                  <th style="padding:10px 6px;text-align:center">종합</th>
                  <th style="padding:10px 6px;text-align:center">C</th>
                  <th style="padding:10px 6px;text-align:center">A</th>
                  <th style="padding:10px 6px;text-align:center">N</th>
                  <th style="padding:10px 6px;text-align:center">S</th>
                  <th style="padding:10px 6px;text-align:center">L</th>
                  <th style="padding:10px 6px;text-align:center">I</th>
                  <th style="padding:10px 6px;text-align:center">M</th>
                </tr>
              </thead>
              <tbody style="border-top:1px solid #1e2a40">
                {table_rows}
              </tbody>
            </table>
          </div>

          <!-- 종목 상세 -->
          <h2 style="color:#63b3ed;font-size:18px;margin-bottom:16px">🔍 종목별 상세 분석</h2>
          {detail_cards}

          <!-- CAN SLIM 설명 -->
          <div style="background:#141824;border-radius:12px;padding:20px;margin-bottom:24px;border:1px solid #1e2a40">
            <h2 style="color:#63b3ed;font-size:16px;margin-top:0">📖 CAN SLIM 7대 요소</h2>
            <table style="width:100%;font-size:13px;border-collapse:collapse">
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold;width:32px">C</td><td style="padding:6px 8px;color:#f0f4ff">분기 EPS 성장 — 전년 동기 대비 +25% 이상</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">A</td><td style="padding:6px 8px;color:#f0f4ff">연간 EPS 성장 — 최근 3년 연평균 +25% 이상</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">N</td><td style="padding:6px 8px;color:#f0f4ff">신고가 근접 — 52주 고점 대비 -15% 이내</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">S</td><td style="padding:6px 8px;color:#f0f4ff">수급 강도 — 기관·외인 순매수 강도</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">L</td><td style="padding:6px 8px;color:#f0f4ff">주도주 — RS 백분위 80위 이상</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">I</td><td style="padding:6px 8px;color:#f0f4ff">기관 매집 — 기관 보유 트렌드 증가</td></tr>
              <tr><td style="padding:6px 8px;color:#63b3ed;font-weight:bold">M</td><td style="padding:6px 8px;color:#f0f4ff">시장 방향 — Follow-through Day 여부</td></tr>
            </table>
          </div>

          <!-- 면책조항 -->
          <div style="color:#4a5568;font-size:12px;text-align:center;padding:16px 0;border-top:1px solid #1e2a40">
            ⚠ 본 내용은 투자 참고용입니다. 손실 책임은 투자자 본인에게 있습니다.<br>
            자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | CAN SLIM 스코어링 엔진
          </div>

        </body>
        </html>
    """).strip()

    return html


# ── 진입점 ───────────────────────────────────────────────────────────
def run(n: int = 5, out_dir: str = "output/blog") -> dict:
    from etl.sns_publisher.card_generator import fetch
    stocks = fetch(n)
    if not stocks:
        raise RuntimeError("DB 조회 실패 — canslim_scores 데이터를 확인하세요.")

    score_date = stocks[0]["score_date"]
    ts  = score_date.strftime("%Y%m%d") if hasattr(score_date, "strftime") else datetime.now().strftime("%Y%m%d")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_path   = out / f"blog_{ts}.md"
    html_path = out / f"blog_{ts}.html"

    md_path.write_text(generate_markdown(stocks, score_date), encoding="utf-8")
    html_path.write_text(generate_html(stocks, score_date), encoding="utf-8")

    return {"markdown": str(md_path), "html": str(html_path), "stocks": stocks}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="CAN SLIM 블로그 포스트 생성기")
    parser.add_argument("--n",   type=int, default=5,            help="TOP N 종목 (기본: 5)")
    parser.add_argument("--out", type=str, default="output/blog", help="출력 디렉터리")
    args = parser.parse_args()

    result = run(n=args.n, out_dir=args.out)
    print(f"마크다운: {result['markdown']}")
    print(f"HTML:     {result['html']}")
