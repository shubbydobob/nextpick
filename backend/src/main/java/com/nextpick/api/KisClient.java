package com.nextpick.api;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.yaml.snakeyaml.Yaml;

import java.io.FileInputStream;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.Map;

/**
 * KIS 인증 공유 클라이언트 — config(키) 로드 + 접근토큰 캐시.
 * 여러 컨트롤러(실시간 시세, 매크로 지수)가 같은 토큰을 공유해
 * 토큰 중복 발급(초당/분당 제한) 문제를 방지한다.
 */
@Component
public class KisClient {

    private static final Logger log = LoggerFactory.getLogger(KisClient.class);
    public static final String BASE = "https://openapi.koreainvestment.com:9443";

    private final RestTemplate rest = new RestTemplate();

    private String cachedToken;
    private Instant tokenExpiry = Instant.EPOCH;
    private Map<String, Object> kisConfig;

    @SuppressWarnings("unchecked")
    public synchronized Map<String, Object> getConfig() throws Exception {
        if (kisConfig != null) return kisConfig;

        // 1순위: 환경변수 (KIS_APP_KEY / KIS_APP_SECRET) — 컨테이너에 파일 불필요
        String envKey = System.getenv("KIS_APP_KEY");
        String envSecret = System.getenv("KIS_APP_SECRET");
        if (envKey != null && !envKey.isBlank() && envSecret != null && !envSecret.isBlank()) {
            kisConfig = Map.of("app_key", envKey, "app_secret", envSecret);
            log.info("KIS config: 환경변수에서 로드");
            return kisConfig;
        }

        // 2순위: KIS_CONFIG_PATH 파일(Docker 볼륨) → 3순위: 로컬 상대경로
        String envPath = System.getenv("KIS_CONFIG_PATH");
        Path yamlPath = (envPath != null && !envPath.isBlank())
                ? Paths.get(envPath)
                : Paths.get("").toAbsolutePath().getParent().resolve("etl/config/kis.yaml");
        try (FileInputStream fis = new FileInputStream(yamlPath.toFile())) {
            kisConfig = new Yaml().load(fis);
        }
        log.info("KIS config: 파일에서 로드 ({})", yamlPath);
        return kisConfig;
    }

    public synchronized String getToken() throws Exception {
        if (cachedToken != null && Instant.now().isBefore(tokenExpiry)) return cachedToken;

        Map<String, Object> cfg = getConfig();
        log.info("KIS 토큰 발급 요청...");
        HttpHeaders h = new HttpHeaders();
        h.setContentType(MediaType.APPLICATION_JSON);
        Map<String, String> body = Map.of(
                "grant_type", "client_credentials",
                "appkey",     (String) cfg.get("app_key"),
                "appsecret",  (String) cfg.get("app_secret")
        );
        ResponseEntity<Map> resp = rest.postForEntity(
                BASE + "/oauth2/tokenP", new HttpEntity<>(body, h), Map.class);

        @SuppressWarnings("unchecked")
        Map<String, Object> data = resp.getBody();
        if (data == null) throw new RuntimeException("토큰 발급 응답 없음");

        cachedToken = (String) data.get("access_token");
        long expiresIn = Long.parseLong(String.valueOf(data.getOrDefault("expires_in", "86400")));
        tokenExpiry = Instant.now().plusSeconds(expiresIn - 600);
        log.info("KIS 토큰 발급 완료 ({}s)", expiresIn);
        return cachedToken;
    }

    /** KIS 인증 헤더 구성 (tr_id별). */
    public HttpHeaders authHeaders(String trId) throws Exception {
        Map<String, Object> cfg = getConfig();
        HttpHeaders headers = new HttpHeaders();
        headers.set("authorization", "Bearer " + getToken());
        headers.set("appkey",   (String) cfg.get("app_key"));
        headers.set("appsecret", (String) cfg.get("app_secret"));
        headers.set("tr_id",    trId);
        headers.set("custtype", "P");
        return headers;
    }
}
