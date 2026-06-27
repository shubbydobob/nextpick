package com.canslim.scoring.scorer;

import com.canslim.domain.DerivedMetric;
import com.canslim.domain.Instrument;
import com.canslim.domain.MarketConfig;
import org.springframework.stereotype.Component;

/**
 * S — Supply and Demand (시가총액 희소성 + 거래량 급증).
 *
 * 채점:
 *   capScore   = max(0, 80 × (1 - marketCapTril / sCapMaxTril))
 *                null 시가총액 → 0점 (실측 데이터 없으면 점수 없음)
 *   surgeScore = volumeRatio20d >= sVolSurgeThreshold 이면
 *                min(20, (ratio - 1) / (threshold - 1) × 20)
 *   최종 = clamp(capScore + surgeScore, 0, 100)
 *
 * sCapMaxTril: 시가총액 상한 (단위: 조원, 기본 10조).
 *   10조 이상 대형주 → capScore = 0
 *   1조: 80 × (1 - 0.1) = 72점
 *   소형주(0.1조): 80 × (1 - 0.01) = 79점
 *
 * 실측 데이터만 사용: market_cap_tril = close_adj × total_shares / 1e12
 * float_shares 근사값(= total_shares) 의존 완전 제거.
 */
@Component
public class SScorer {

    public Double score(Instrument instrument, DerivedMetric dm, MarketConfig cfg) {
        double capMaxTril = cfg.getSCapMaxTril() != null
                ? cfg.getSCapMaxTril().doubleValue()
                : 10.0;
        double surgeThreshold = cfg.getSVolSurgeThreshold() != null
                ? cfg.getSVolSurgeThreshold().doubleValue()
                : 1.5;

        // 시가총액 희소성 점수 (실측값 없으면 0점)
        double capScore = 0.0;
        if (dm != null && dm.getMarketCapTril() != null) {
            double capTril = dm.getMarketCapTril().doubleValue();
            capScore = Math.max(0.0, 80.0 * (1.0 - capTril / capMaxTril));
        }

        // 거래량 급증 점수
        double surgeScore = 0.0;
        if (dm != null && dm.getVolumeRatio20d() != null) {
            double ratio = dm.getVolumeRatio20d().doubleValue();
            if (ratio >= surgeThreshold && surgeThreshold > 1.0) {
                surgeScore = Math.min(20.0, (ratio - 1.0) / (surgeThreshold - 1.0) * 20.0);
            }
        }

        return Math.min(100.0, Math.max(0.0, capScore + surgeScore));
    }
}
