"""
블로그 포스트 자동 생성기

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
        f"# {ds} 성장주 TOP {len(stocks)} 분석",
        "",
        f"> **{ds_compact}** 기준으로 7대 성장 요소를 종합 스코어링한 결과입니다.",
        "> 분기 EPS 성장, 연간 성장성, 신고가 근접도,",
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

    # ── 7대 요소 설명 ──
    lines += [
        "## 📖 7대 성장 요소란?",
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
            "#### 팩터 분석",
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
        "본 분석은 성장주 스코어링 방법론에 따른 **참고용 정보**입니다.",
        "투자 판단 및 그에 따른 손익은 전적으로 투자자 본인에게 귀속됩니다.",
        "과거 성과가 미래 수익을 보장하지 않습니다.",
        "",
        f"*자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 성장주스크리너*",
        "",
        "**태그**: #성장주 #주식스크리너 #한국주식 #주식공부 ",
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
          <title>{ds} 성장주 TOP {len(stocks)} 분석</title>
        </head>
        <body style="margin:0;padding:20px;background:#0c0f18;color:#f0f4ff;font-family:'Malgun Gothic',sans-serif;max-width:800px;margin:0 auto">

          <!-- 헤더 -->
          <div style="border-top:4px solid #63b3ed;padding-top:24px;margin-bottom:32px">
            <div style="color:#63b3ed;font-size:14px;font-weight:bold;letter-spacing:2px">성장주 레이더</div>
            <h1 style="margin:8px 0 4px;font-size:32px;color:#f0f4ff">{ds}<br>TOP {len(stocks)} 성장주 분석</h1>
            <p style="color:#8899aa;font-size:14px;margin:0">7대 성장 요소로 선별한 오늘의 주도주</p>
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

          <!-- 7대 요소 설명 -->
          <div style="background:#141824;border-radius:12px;padding:20px;margin-bottom:24px;border:1px solid #1e2a40">
            <h2 style="color:#63b3ed;font-size:16px;margin-top:0">📖 7대 성장 요소</h2>
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
            자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 성장주스크리너
          </div>

        </body>
        </html>
    """).strip()

    return html


# ── 팩터 자동 해석 텍스트 ────────────────────────────────────────────
def _interp_c(score, yoy) -> str:
    yoy_t = f"전년 동기 대비 EPS {_pct(yoy)} 성장" if yoy is not None else "EPS 데이터 미확인"
    if score is None: return f"DART 재무 데이터가 확인되지 않습니다. {yoy_t}."
    v = float(score)
    if v >= 80: return f"분기 EPS가 매우 강하게 성장했습니다. {yoy_t}. 기준(+25% 이상)을 크게 상회합니다."
    if v >= 60: return f"분기 EPS 성장이 양호합니다. {yoy_t}. 기준을 충족하는 수준입니다."
    if v >= 45: return f"분기 EPS 성장이 보통 수준입니다. {yoy_t}. 추가 확인이 필요합니다."
    return f"분기 EPS 성장이 부진합니다. {yoy_t}. 매수 기준 미달입니다."

def _interp_a(score, cagr) -> str:
    cagr_t = f"3년 연평균 EPS 성장률 {_pct(cagr, True)}" if cagr is not None else "장기 성장 데이터 미확인"
    if score is None: return f"DART 연간 재무 데이터가 확인되지 않습니다. {cagr_t}."
    v = float(score)
    if v >= 80: return f"장기 EPS 성장 트렌드가 매우 강합니다. {cagr_t}. 지속적 성장 패턴입니다."
    if v >= 60: return f"장기 성장성이 양호합니다. {cagr_t}. 안정적인 성장 기업으로 볼 수 있습니다."
    if v >= 45: return f"장기 성장이 보통 수준입니다. {cagr_t}. 성장 모멘텀이 강하지 않습니다."
    return f"장기 EPS 성장이 부진합니다. {cagr_t}. 성장주로서의 매력이 낮습니다."

def _interp_n(score, h52) -> str:
    h52_t = f"52주 고점 대비 {_pct(h52)}" if h52 is not None else "고점 데이터 미확인"
    if score is None: return f"신고가 데이터를 확인할 수 없습니다."
    v = float(score)
    if v >= 80: return f"52주 신고가 근방에서 거래 중입니다. {h52_t}. 주가 모멘텀이 매우 강합니다."
    if v >= 60: return f"신고가 수준에 근접해 있습니다. {h52_t}. 상승 추세가 유지되고 있습니다."
    if v >= 45: return f"신고가에서 어느 정도 벗어나 있습니다. {h52_t}. 주가 모멘텀이 다소 약합니다."
    return f"52주 고점에서 크게 하락한 상태입니다. {h52_t}. 매수 기준에 미달합니다."

def _interp_s(score, inst, foreign) -> str:
    inst_t    = f"기관 순매수 {_buy(inst)}" if inst is not None else "기관 데이터 미확인"
    foreign_t = f"외인 순매수 {_buy(foreign)}" if foreign is not None else ""
    detail    = ", ".join(t for t in [inst_t, foreign_t] if t)
    if score is None: return f"수급 데이터를 확인할 수 없습니다."
    v = float(score)
    if v >= 80: return f"기관·외인 수급이 매우 강합니다. {detail}. 스마트머니 유입이 활발합니다."
    if v >= 60: return f"수급이 양호합니다. {detail}. 기관·외인의 지속적 관심이 확인됩니다."
    if v >= 45: return f"수급이 보통 수준입니다. {detail}. 뚜렷한 방향성이 없습니다."
    return f"수급이 부진합니다. {detail}. 기관·외인의 관심이 낮은 상태입니다."

def _interp_l(score, rs) -> str:
    rs_t = f"RS 백분위 {_fmt(rs)}위" if rs is not None else "RS 데이터 미확인"
    if score is None: return f"상대강도 데이터를 확인할 수 없습니다."
    v = float(score)
    if v >= 80: return f"시장 대비 주가 강도가 매우 높습니다. {rs_t}. 상위 10% 주도주 요건을 충족합니다."
    if v >= 60: return f"시장 대비 강세를 보입니다. {rs_t}. 주도주 후보군에 속합니다."
    if v >= 45: return f"시장 평균 수준입니다. {rs_t}. 주도주보다는 추종주에 가깝습니다."
    return f"시장 대비 약세입니다. {rs_t}. 성장주 관점에서 매수 우선순위가 낮습니다."

def _interp_i(score) -> str:
    if score is None: return "기관 참여도 데이터를 확인할 수 없습니다."
    v = float(score)
    if v >= 80: return "기관 보유 비중이 높고 증가 추세입니다. 펀드매니저들의 적극적인 매집이 진행 중입니다."
    if v >= 60: return "기관 참여가 양호합니다. 안정적인 기관 보유 기반이 형성되어 있습니다."
    if v >= 45: return "기관 참여가 보통 수준입니다. 기관의 적극적 매집 신호는 확인되지 않습니다."
    return "기관 참여가 낮습니다. 기관의 관심이 부족한 종목은 급격한 변동에 취약합니다."

def _interp_m(score) -> str:
    if score is None: return "시장 방향 데이터를 확인할 수 없습니다."
    v = float(score)
    if v >= 80: return "현재 시장이 확실한 상승 추세에 있습니다. Follow-through Day가 확인된 강세장 국면입니다."
    if v >= 60: return "시장이 전반적으로 우호적인 국면입니다. 신규 매수에 유리한 환경입니다."
    if v >= 45: return "시장 방향이 불분명합니다. 신중한 포지션 관리가 필요합니다."
    return "시장이 조정 또는 약세 국면입니다. 신규 매수보다 관망이 적절합니다."

def _verdict(comp) -> tuple[str, str]:
    """종합 판정 문장과 액션 반환."""
    if comp >= 80: return "강력 매수 후보", "7대 성장 요소를 대부분 충족하는 우량 성장주입니다. 적절한 매수 시점을 확인하세요."
    if comp >= 65: return "매수 검토",      "주요 요소를 충족하는 성장주입니다. 취약 팩터를 보완 확인 후 매수를 검토하세요."
    if comp >= 50: return "관망",            "일부 요소가 기준을 충족하지 못합니다. 추가 개선 신호를 확인한 후 접근하세요."
    return "매수 보류",   "성장주 기준 충족도가 낮습니다. 현시점에서는 매수보다 관망이 적절합니다."

def _strengths_weaknesses(s) -> tuple[list[str], list[str]]:
    """80+ 팩터 → 강점, 45 미만 팩터 → 약점."""
    factors = [
        ("C 분기 EPS 성장", s["c"]),
        ("A 연간 성장성",   s["a"]),
        ("N 신고가 근접",   s["n"]),
        ("S 수급 강도",     s["s"]),
        ("L 상대 강도",     s["l"]),
        ("I 기관 참여",     s["i"]),
        ("M 시장 방향",     s["m"]),
    ]
    strong = [name for name, v in factors if v is not None and float(v) >= 80]
    weak   = [name for name, v in factors if v is None or float(v) < 45]
    return strong, weak


# ── 종목 상세 마크다운 ────────────────────────────────────────────────
def generate_stock_markdown(s: dict, score_date, rank: int | None = None) -> str:
    ds   = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    comp = float(s["composite"] or 0)
    cr   = float(s["cr"]) if s["cr"] is not None else None
    cr_t = f" ({_pct(cr)})" if cr is not None else ""
    rank_t = f"{rank}위 · " if rank else ""
    verdict_label, verdict_desc = _verdict(comp)
    strong, weak = _strengths_weaknesses(s)

    lines: list[str] = []

    # 제목
    lines += [
        f"# {s['name']}({s['ticker']}) 성장주 분석 — {ds}",
        "",
        f"> {rank_t}{s['market']} · {s.get('sector') or '—'}  |  종합 점수 **{comp:.0f}점**  |  판정: **{verdict_label}**",
        "",
        "---",
        "",
    ]

    # 투자 요약 박스
    lines += [
        "## 💡 투자 요약",
        "",
        f"| 항목 | 내용 |",
        f"|------|------|",
        f"| 현재가 | {_price(s['close'])}{cr_t} |",
        f"| 시가총액 | {_cap(s['cap'])} |",
        f"| 종합 점수 | **{comp:.0f}점** ({_score_label(s['composite'])}) |",
        f"| 종합 판정 | **{verdict_label}** |",
    ]
    if strong:
        lines.append(f"| 강점 팩터 | {', '.join(strong)} |")
    if weak:
        lines.append(f"| 약점 팩터 | {', '.join(weak)} |")
    lines += ["", verdict_desc, "", "---", ""]

    # 팩터별 상세
    lines += ["## 📊 팩터 상세 분석", ""]

    factor_data = [
        ("C", "분기 EPS 성장 (Current Quarterly Earnings)",
         s["c"], _interp_c(s["c"], s.get("yoy")),
         f"YoY {_pct(s.get('yoy'))}"),
        ("A", "연간 EPS 성장 (Annual Earnings Growth)",
         s["a"], _interp_a(s["a"], s.get("cagr")),
         f"3yr CAGR {_pct(s.get('cagr'), True)}"),
        ("N", "신고가 근접 (New Highs)",
         s["n"], _interp_n(s["n"], s.get("h52")),
         f"52주 고점 대비 {_pct(s.get('h52'))}"),
        ("S", "수급 강도 (Supply & Demand)",
         s["s"], _interp_s(s["s"], s.get("inst"), s.get("foreign")),
         f"기관 {_buy(s.get('inst'))} / 외인 {_buy(s.get('foreign'))}"),
        ("L", "상대 강도 (Leader or Laggard)",
         s["l"], _interp_l(s["l"], s.get("rs")),
         f"RS 백분위 {_fmt(s.get('rs'))}위"),
        ("I", "기관 참여 (Institutional Sponsorship)",
         s["i"], _interp_i(s["i"]), ""),
        ("M", "시장 방향 (Market Direction)",
         s["m"], _interp_m(s["m"]), ""),
    ]

    for lbl, title, score, interp, detail in factor_data:
        bar = "█" * max(1, int((float(score) if score else 0) / 10)) + "░" * (10 - max(1, int((float(score) if score else 0) / 10)))
        lines += [
            f"### {lbl}. {title}",
            "",
            f"**점수: {_fmt(score)}점** `{bar}` {_score_label(score)}",
            *([ f"*{detail}*" ] if detail else []),
            "",
            interp,
            "",
        ]

    # 핵심 수치 요약
    lines += [
        "---",
        "",
        "## 📈 핵심 수치 요약",
        "",
        "| 지표 | 수치 |",
        "|------|------|",
        f"| 분기 EPS 성장률 (YoY) | {_pct(s.get('yoy'))} |",
        f"| 3년 연평균 EPS 성장 (CAGR) | {_pct(s.get('cagr'), True)} |",
        f"| RS 백분위 | {_fmt(s.get('rs'))}위 |",
        f"| 기관 순매수 (10일) | {_buy(s.get('inst'))} |",
        f"| 외인 순매수 (10일) | {_buy(s.get('foreign'))} |",
        f"| 52주 고점 대비 | {_pct(s.get('h52'))} |",
        "",
        "---",
        "",
    ]

    # 면책조항
    lines += [
        "## ⚠️ 투자 유의사항",
        "",
        "본 분석은 성장주 스코어링 방법론에 따른 **참고용 자동 생성 정보**입니다.",
        "투자 판단 및 손익은 전적으로 투자자 본인에게 귀속됩니다.",
        "과거 성과가 미래 수익을 보장하지 않습니다.",
        "",
        f"*자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 성장주스크리너*",
        "",
        f"**태그**: #{s['name']} #{s['ticker']} #성장주 #주식분석 #한국주식 ",
    ]

    return "\n".join(lines)


# ── 종목 상세 HTML ────────────────────────────────────────────────────
def generate_stock_html(s: dict, score_date, rank: int | None = None) -> str:
    ds   = score_date.strftime("%Y년 %m월 %d일") if hasattr(score_date, "strftime") else str(score_date)
    comp = float(s["composite"] or 0)
    cr   = float(s["cr"]) if s["cr"] is not None else None
    cr_t = (f"<span style='color:{'#34d399' if (cr or 0) > 0 else '#f87171'}'>"
            f"({_pct(cr)})</span>") if cr is not None else ""
    rank_t = f"{rank}위 · " if rank else ""

    def sc(v): return score_color(v)  # score_color defined in generate_html scope — redefine here
    def score_color(v) -> str:
        if v is None: return "#8899aa"
        v = float(v)
        if v >= 80: return "#34d399"
        if v >= 60: return "#6ee7b7"
        if v >= 45: return "#fbbf24"
        if v >= 30: return "#fb923c"
        return "#f87171"

    verdict_label, verdict_desc = _verdict(comp)
    strong, weak = _strengths_weaknesses(s)
    c_c = score_color(comp)

    factor_data = [
        ("C", "분기 EPS 성장", s["c"], _interp_c(s["c"], s.get("yoy")),   f"YoY {_pct(s.get('yoy'))}"),
        ("A", "연간 성장성",   s["a"], _interp_a(s["a"], s.get("cagr")),   f"3yr CAGR {_pct(s.get('cagr'), True)}"),
        ("N", "신고가 근접",   s["n"], _interp_n(s["n"], s.get("h52")),    f"52주 고점 대비 {_pct(s.get('h52'))}"),
        ("S", "수급 강도",     s["s"], _interp_s(s["s"], s.get("inst"), s.get("foreign")), f"기관 {_buy(s.get('inst'))} / 외인 {_buy(s.get('foreign'))}"),
        ("L", "상대 강도",     s["l"], _interp_l(s["l"], s.get("rs")),     f"RS 백분위 {_fmt(s.get('rs'))}위"),
        ("I", "기관 참여",     s["i"], _interp_i(s["i"]),                  ""),
        ("M", "시장 방향",     s["m"], _interp_m(s["m"]),                  ""),
    ]

    factor_blocks = ""
    for lbl, title, score, interp, detail in factor_data:
        fsc   = score_color(score)
        bar_w = max(4, int(float(score) if score else 0))
        factor_blocks += dedent(f"""
            <div style="background:#141824;border-radius:10px;padding:20px;margin-bottom:16px;border-left:4px solid {fsc}">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <span style="font-size:22px;font-weight:bold;color:{fsc};width:28px">{lbl}</span>
                <span style="font-weight:bold;color:#f0f4ff;font-size:16px">{title}</span>
                <span style="margin-left:auto;font-size:24px;font-weight:bold;color:{fsc}">{_fmt(score)}</span>
              </div>
              <div style="background:#0c0f18;border-radius:4px;height:6px;margin-bottom:10px">
                <div style="background:{fsc};width:{bar_w}%;height:100%;border-radius:4px"></div>
              </div>
              {"<div style='color:#8899aa;font-size:12px;margin-bottom:8px'>" + detail + "</div>" if detail else ""}
              <div style="color:#c8d3e8;font-size:14px;line-height:1.6">{interp}</div>
            </div>
        """)

    strong_html = "".join(
        f"<span style='background:#1a3a2a;color:#34d399;padding:4px 10px;border-radius:12px;font-size:13px;margin:3px'>{t}</span>"
        for t in strong
    ) or "<span style='color:#8899aa;font-size:13px'>—</span>"

    weak_html = "".join(
        f"<span style='background:#3a1a1a;color:#f87171;padding:4px 10px;border-radius:12px;font-size:13px;margin:3px'>{t}</span>"
        for t in weak
    ) or "<span style='color:#8899aa;font-size:13px'>—</span>"

    html = dedent(f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{s['name']}({s['ticker']}) 성장주 분석 — {ds}</title>
        </head>
        <body style="margin:0;padding:20px;background:#0c0f18;color:#f0f4ff;font-family:'Malgun Gothic',sans-serif;max-width:800px;margin:0 auto">

          <!-- 헤더 -->
          <div style="border-top:4px solid #63b3ed;padding-top:24px;margin-bottom:28px">
            <div style="color:#63b3ed;font-size:13px;letter-spacing:2px;margin-bottom:8px">
              성장주 종목 분석 · {ds}
            </div>
            <h1 style="margin:0 0 6px;font-size:36px;color:#f0f4ff">
              {rank_t}{s['name']}
              <span style="font-size:20px;color:#8899aa;font-weight:normal">({s['ticker']})</span>
            </h1>
            <div style="color:#8899aa;font-size:14px">{s['market']} · {s.get('sector') or '—'}</div>
          </div>

          <!-- 점수 + 현재가 히어로 -->
          <div style="display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap">
            <div style="background:#141824;border-radius:12px;padding:20px;flex:1;min-width:160px;text-align:center">
              <div style="color:#8899aa;font-size:12px;margin-bottom:6px">종합 점수</div>
              <div style="font-size:56px;font-weight:bold;color:{c_c};line-height:1">{comp:.0f}</div>
              <div style="color:#8899aa;font-size:13px;margin-top:4px">{_score_label(s['composite'])}</div>
            </div>
            <div style="background:#141824;border-radius:12px;padding:20px;flex:1;min-width:160px;text-align:center">
              <div style="color:#8899aa;font-size:12px;margin-bottom:6px">현재가</div>
              <div style="font-size:28px;font-weight:bold;color:#f0f4ff">{_price(s['close'])}</div>
              <div style="margin-top:4px">{cr_t}</div>
            </div>
            <div style="background:#141824;border-radius:12px;padding:20px;flex:1;min-width:160px;text-align:center">
              <div style="color:#8899aa;font-size:12px;margin-bottom:6px">종합 판정</div>
              <div style="font-size:20px;font-weight:bold;color:{c_c}">{verdict_label}</div>
              <div style="color:#8899aa;font-size:12px;margin-top:4px">시총 {_cap(s['cap'])}</div>
            </div>
          </div>

          <!-- 강점/약점 -->
          <div style="background:#141824;border-radius:12px;padding:20px;margin-bottom:28px">
            <div style="margin-bottom:12px">
              <span style="color:#34d399;font-weight:bold;font-size:14px">✅ 강점 팩터</span><br>
              <div style="margin-top:8px">{strong_html}</div>
            </div>
            <div>
              <span style="color:#f87171;font-weight:bold;font-size:14px">⚠ 약점 팩터</span><br>
              <div style="margin-top:8px">{weak_html}</div>
            </div>
            <div style="margin-top:16px;color:#c8d3e8;font-size:14px;line-height:1.6;padding-top:12px;border-top:1px solid #1e2a40">
              {verdict_desc}
            </div>
          </div>

          <!-- 팩터 상세 -->
          <h2 style="color:#63b3ed;font-size:18px;margin-bottom:16px">📊 팩터 상세 분석</h2>
          {factor_blocks}

          <!-- 핵심 수치 -->
          <h2 style="color:#63b3ed;font-size:18px;margin:28px 0 16px">📈 핵심 수치</h2>
          <div style="background:#141824;border-radius:12px;padding:4px 0;margin-bottom:28px">
            {"".join(
              f"<div style='display:flex;justify-content:space-between;padding:12px 20px;border-bottom:1px solid #1e2a40'>"
              f"<span style='color:#8899aa;font-size:14px'>{k}</span>"
              f"<span style='font-weight:bold;color:#f0f4ff;font-size:14px'>{v}</span></div>"
              for k, v in [
                ("분기 EPS 성장률 (YoY)", _pct(s.get("yoy"))),
                ("3년 연평균 EPS 성장 (CAGR)", _pct(s.get("cagr"), True)),
                ("RS 백분위", f"{_fmt(s.get('rs'))}위"),
                ("기관 순매수 (10일)", _buy(s.get("inst"))),
                ("외인 순매수 (10일)", _buy(s.get("foreign"))),
                ("52주 고점 대비", _pct(s.get("h52"))),
              ]
            )}
          </div>

          <!-- 면책조항 -->
          <div style="color:#4a5568;font-size:12px;text-align:center;padding:16px 0;border-top:1px solid #1e2a40">
            ⚠ 투자 참고용 자동 생성 정보입니다. 손실 책임은 투자자 본인에게 있습니다.<br>
            자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 성장주스크리너
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
        raise RuntimeError("DB 조회 실패 — nextpick_scores 데이터를 확인하세요.")

    score_date = stocks[0]["score_date"]
    ts  = score_date.strftime("%Y%m%d") if hasattr(score_date, "strftime") else datetime.now().strftime("%Y%m%d")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_path   = out / f"blog_{ts}.md"
    html_path = out / f"blog_{ts}.html"

    md_path.write_text(generate_markdown(stocks, score_date), encoding="utf-8")
    html_path.write_text(generate_html(stocks, score_date), encoding="utf-8")

    # 종목별 상세 포스트
    stock_files = []
    for rank, s in enumerate(stocks, 1):
        ticker = s["ticker"]
        s_md   = out / f"stock_{ts}_{ticker}.md"
        s_html = out / f"stock_{ts}_{ticker}.html"
        s_md.write_text(generate_stock_markdown(s, score_date, rank), encoding="utf-8")
        s_html.write_text(generate_stock_html(s, score_date, rank), encoding="utf-8")
        stock_files.append({"ticker": ticker, "markdown": str(s_md), "html": str(s_html)})

    return {"markdown": str(md_path), "html": str(html_path),
            "stocks": stocks, "stock_files": stock_files}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="블로그 포스트 생성기")
    parser.add_argument("--n",   type=int, default=5,            help="TOP N 종목 (기본: 5)")
    parser.add_argument("--out", type=str, default="output/blog", help="출력 디렉터리")
    args = parser.parse_args()

    result = run(n=args.n, out_dir=args.out)
    print(f"마크다운: {result['markdown']}")
    print(f"HTML:     {result['html']}")
