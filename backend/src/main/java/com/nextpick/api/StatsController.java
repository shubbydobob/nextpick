package com.nextpick.api;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * POST /api/stats/visit  — 방문 기록 + 누적 방문자 수 반환
 * GET  /api/stats/visits — 누적 방문자 수 조회
 */
@RestController
@RequestMapping("/api/stats")
public class StatsController {

    private final JdbcTemplate jdbc;

    public StatsController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @PostMapping("/visit")
    public Map<String, Long> recordVisit() {
        jdbc.update("INSERT INTO page_visits (visited_at) VALUES (NOW())");
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM page_visits", Long.class);
        return Map.of("total", total == null ? 0L : total);
    }

    @GetMapping("/visits")
    public Map<String, Long> getVisits() {
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM page_visits", Long.class);
        return Map.of("total", total == null ? 0L : total);
    }
}
