package com.nextpick.repository;

import com.nextpick.domain.MarketConfig;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface MarketConfigRepository extends JpaRepository<MarketConfig, Long> {

    Optional<MarketConfig> findByMarketAndActiveTrue(String market);
}
