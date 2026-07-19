package com.nextpick.scoring.scorer;

import com.nextpick.domain.DerivedMetric;
import com.nextpick.domain.MarketConfig;
import org.springframework.stereotype.Component;

/**
 * I — Institutional Sponsorship (기관 스폰서십).
 *
 * ── KR (일별 외인/기관 순매수) — 채점 (기준점 50):
 *   instBuyScore   = clamp((instNetBuy10d  / iNetBuyThreshold) × 30, -30, +30)
 *   foreignScore   = clamp((foreignNetBuy10d / iNetBuyThreshold) × 20, -20, +20)
 *   trendBonus     = instTrendFlag × 5  (-1→-5, 0→0, 1→+5, 2→+10)
 *   최종 = clamp(50 + instBuyScore + foreignScore + trendBonus, 0, 100)
 *
 * ── US (13F 분기 기관보유) — 채점 (기준점 50):
 *   ownershipScore = clamp((instPctHeld - 0.5) × 40, -20, +20)   // 50% 중립, 보유 강할수록 +
 *   breadthScore   = clamp(instAccumBreadth / 10 × 15, -15, +15) // 상위기관 순매집 breadth
 *   최종 = clamp(50 + ownershipScore + breadthScore, 0, 100)
 *   근거: 오닐 원전 I는 '기관 스폰서십의 존재+증가'. US는 일별 플로우가 없어 13F(분기·yfinance 집계) 사용.
 *
 * 데이터 없음 → null 반환. weightedComposite의 "null 분모 제외"로 5팩터 정규화(50 고정 시 랭킹 왜곡).
 * iNetBuyThreshold: 유의미한 순매수로 간주할 기준 금액(또는 수량). DB 설정값.
 */
@Component
public class IScorer {

    public Double score(DerivedMetric dm, MarketConfig cfg) {
        if (dm == null) return null;

        // ── US 13F 분기 (inst_pct_held가 채워진 종목) ─────────────
        if (dm.getInstPctHeld() != null) {
            double pct = dm.getInstPctHeld().doubleValue();          // 0~1
            double ownershipScore = clamp((pct - 0.5) * 40.0, -20.0, 20.0);
            double breadthScore = 0.0;
            if (dm.getInstAccumBreadth() != null) {
                breadthScore = clamp(dm.getInstAccumBreadth() / 10.0 * 15.0, -15.0, 15.0);
            }
            return clamp(50.0 + ownershipScore + breadthScore, 0.0, 100.0);
        }

        // ── KR 일별 순매수 — 데이터가 전혀 없으면 null (weightedComposite가 분모 제외) ──
        if (dm.getInstNetBuy10d() == null
                && dm.getForeignNetBuy10d() == null
                && dm.getInstTrendFlag() == null) {
            return null;
        }

        double threshold = cfg.getINetBuyThreshold() != null
                ? cfg.getINetBuyThreshold().doubleValue()
                : 1.0;

        double instScore = 0.0;
        if (dm.getInstNetBuy10d() != null && threshold != 0) {
            double raw = dm.getInstNetBuy10d().doubleValue() / threshold * 30.0;
            instScore = Math.min(30.0, Math.max(-30.0, raw));
        }

        double foreignScore = 0.0;
        if (dm.getForeignNetBuy10d() != null && threshold != 0) {
            double raw = dm.getForeignNetBuy10d().doubleValue() / threshold * 20.0;
            foreignScore = Math.min(20.0, Math.max(-20.0, raw));
        }

        double trendBonus = 0.0;
        if (dm.getInstTrendFlag() != null) {
            trendBonus = dm.getInstTrendFlag() * 5.0;
        }

        return Math.min(100.0, Math.max(0.0, 50.0 + instScore + foreignScore + trendBonus));
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.min(hi, Math.max(lo, v));
    }
}
