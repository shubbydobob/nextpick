package com.canslim.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;

/**
 * 거시 경제 지표 프록시 — Yahoo Finance v8 chart API (종목별 병렬 조회).
 * GET /api/macro/quotes
 */
@RestController
@RequestMapping("/api/macro")
public class MacroController {

    private static final Logger log = LoggerFactory.getLogger(MacroController.class);

    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(8))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final ExecutorService POOL  = Executors.newFixedThreadPool(4);

    private final KisClient kis;
    private final RestTemplate rest = new RestTemplate();
    public MacroController(KisClient kis) { this.kis = kis; }

    /** 국내 지수는 KIS 실시간으로 (symbol → KIS 업종코드). 나머지는 Yahoo. */
    private static final Map<String, String> KIS_INDEX = Map.of("^KS11", "0001", "^KQ11", "1001");

    /** symbol → 한국어 표시명 (순서 유지) */
    private static final LinkedHashMap<String, String> SYMBOLS = new LinkedHashMap<>();
    static {
        SYMBOLS.put("^KS11",    "코스피");
        SYMBOLS.put("^KQ11",    "코스닥");
        SYMBOLS.put("^IXIC",    "나스닥");
        SYMBOLS.put("NQ=F",     "나스닥선물");
        SYMBOLS.put("ES=F",     "S&P500선물");
        SYMBOLS.put("^SOX",     "필라델피아반도체");
        SYMBOLS.put("BTC-USD",  "비트코인");
        SYMBOLS.put("KRW=X",    "달러/원");
        SYMBOLS.put("^TNX",     "미국10Y금리");
        SYMBOLS.put("^VIX",     "공포지수(VIX)");
        SYMBOLS.put("GC=F",     "금");
        SYMBOLS.put("DX-Y.NYB", "달러인덱스");
    }

    public record QuoteDto(
            String symbol, String name,
            Double price, Double change, Double changePct,
            String currency, String marketState) {}

    /** KRX 코스피 업종 지수 (FID_COND_MRKT_DIV_CODE=U). 시총 큰 순 정렬로 나열. */
    private static final LinkedHashMap<String, String> SECTOR_INDICES = new LinkedHashMap<>();
    static {
        SECTOR_INDICES.put("0010", "전기전자");
        SECTOR_INDICES.put("0018", "금융업");
        SECTOR_INDICES.put("0005", "화학");
        SECTOR_INDICES.put("0012", "운수장비");
        SECTOR_INDICES.put("0006", "의약품");
        SECTOR_INDICES.put("0008", "철강금속");
        SECTOR_INDICES.put("0013", "유통업");
        SECTOR_INDICES.put("0021", "서비스업");
        SECTOR_INDICES.put("0015", "건설업");
        SECTOR_INDICES.put("0002", "음식료품");
        SECTOR_INDICES.put("0009", "기계");
        SECTOR_INDICES.put("0017", "통신업");
        SECTOR_INDICES.put("0020", "보험");
        SECTOR_INDICES.put("0019", "증권");
        SECTOR_INDICES.put("0014", "전기가스");
        SECTOR_INDICES.put("0016", "운수창고");
        SECTOR_INDICES.put("0011", "의료정밀");
        SECTOR_INDICES.put("0007", "비금속광물");
        SECTOR_INDICES.put("0003", "섬유의복");
        SECTOR_INDICES.put("0004", "종이목재");
    }

    /** GET /api/macro/sectors — KRX 코스피 업종 지수 실시간 등락률 (finviz식 섹터 히트맵용). */
    @GetMapping("/sectors")
    public ResponseEntity<List<QuoteDto>> getSectorIndices() {
        List<Future<QuoteDto>> futures = SECTOR_INDICES.entrySet().stream()
                .map(e -> POOL.submit(() -> fetchKisIndex(e.getKey(), e.getKey(), e.getValue())))
                .toList();
        List<QuoteDto> result = new ArrayList<>();
        for (Future<QuoteDto> f : futures) {
            try {
                QuoteDto q = f.get(10, TimeUnit.SECONDS);
                if (q != null) result.add(q);
            } catch (Exception ignore) { }
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/quotes")
    public ResponseEntity<List<QuoteDto>> getQuotes() {
        List<Future<QuoteDto>> futures = SYMBOLS.entrySet().stream()
                .map(e -> POOL.submit(() -> fetchOne(e.getKey(), e.getValue())))
                .toList();

        List<QuoteDto> result = new ArrayList<>();
        for (Future<QuoteDto> f : futures) {
            try {
                QuoteDto q = f.get(10, TimeUnit.SECONDS);
                if (q != null) result.add(q);
            } catch (Exception e) {
                // 개별 실패는 무시
            }
        }
        return ResponseEntity.ok(result);
    }

    /** GET /api/macro/debug?iscd=0001 — KIS 지수 원본 응답 확인용(필드/tr_id 검증). */
    @GetMapping("/debug")
    public ResponseEntity<Map<String, Object>> debug(
            @RequestParam(value = "iscd", defaultValue = "0001") String iscd) {
        Map<String, Object> r = new LinkedHashMap<>();
        try {
            HttpHeaders h = kis.authHeaders("FHPUP02100000");
            String url = KisClient.BASE + "/uapi/domestic-stock/v1/quotations/inquire-index-price"
                    + "?FID_COND_MRKT_DIV_CODE=U&FID_INPUT_ISCD=" + iscd;
            ResponseEntity<Map> resp = rest.exchange(url, HttpMethod.GET, new HttpEntity<>(h), Map.class);
            r.put("httpStatus", resp.getStatusCode().value());
            Map<?, ?> body = resp.getBody();
            if (body != null) {
                r.put("rt_cd", body.get("rt_cd"));
                r.put("msg1", body.get("msg1"));
                r.put("output", body.get("output"));   // 전체 output — 필드명 확인용
            }
        } catch (org.springframework.web.client.HttpStatusCodeException he) {
            r.put("httpStatus", he.getStatusCode().value());
            r.put("body", he.getResponseBodyAsString());
        } catch (Exception e) {
            r.put("error", String.valueOf(e));
        }
        return ResponseEntity.ok(r);
    }

    private QuoteDto fetchOne(String symbol, String name) {
        // 국내 지수는 KIS 실시간 우선, 실패 시 Yahoo 폴백
        String iscd = KIS_INDEX.get(symbol);
        if (iscd != null) {
            QuoteDto kisQ = fetchKisIndex(iscd, symbol, name);
            if (kisQ != null) return kisQ;
        }
        return fetchYahoo(symbol, name);
    }

    /** KIS 국내업종 현재지수 (FHPUP02100000). 코스피=0001, 코스닥=1001. */
    private QuoteDto fetchKisIndex(String iscd, String symbol, String name) {
        try {
            HttpHeaders h = kis.authHeaders("FHPUP02100000");
            String url = KisClient.BASE + "/uapi/domestic-stock/v1/quotations/inquire-index-price"
                    + "?FID_COND_MRKT_DIV_CODE=U&FID_INPUT_ISCD=" + iscd;
            ResponseEntity<Map> resp = rest.exchange(url, HttpMethod.GET, new HttpEntity<>(h), Map.class);
            if (!resp.getStatusCode().is2xxSuccessful() || resp.getBody() == null) return null;
            Object o = resp.getBody().get("output");
            if (!(o instanceof Map<?, ?> out)) return null;

            double price  = parseD(out.get("bstp_nmix_prpr"));       // 현재 지수
            if (price == 0) return null;
            double change = parseD(out.get("bstp_nmix_prdy_vrss"));  // 전일 대비
            double pct    = parseD(out.get("bstp_nmix_prdy_ctrt"));  // 전일 대비율
            // 부호 보정 (prdy_vrss_sign: 1/2 상승, 4/5 하락, 3 보합)
            String sign = String.valueOf(out.get("prdy_vrss_sign"));
            if ("4".equals(sign) || "5".equals(sign)) { pct = -Math.abs(pct); change = -Math.abs(change); }
            else if ("1".equals(sign) || "2".equals(sign)) { pct = Math.abs(pct); change = Math.abs(change); }

            return new QuoteDto(symbol, name, price, change, pct, "KRW", "REGULAR");
        } catch (Exception e) {
            log.debug("KIS 지수 {} 조회 실패: {}", iscd, e.getMessage());
            return null;
        }
    }

    private static double parseD(Object o) {
        try { return Double.parseDouble(String.valueOf(o).replace(",", "").trim()); }
        catch (Exception e) { return 0; }
    }

    private QuoteDto fetchYahoo(String symbol, String name) {
        // Yahoo Finance v8 chart API — 단일 심볼
        String url = "https://query1.finance.yahoo.com/v8/finance/chart/"
                + symbol.replace("^", "%5E")
                + "?interval=1d&range=2d&includePrePost=false";
        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("User-Agent",
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            + "AppleWebKit/537.36 (KHTML, like Gecko) "
                            + "Chrome/125.0.0.0 Safari/537.36")
                    .header("Accept", "application/json,*/*")
                    .header("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.8")
                    .header("Referer", "https://finance.yahoo.com/")
                    .timeout(Duration.ofSeconds(8))
                    .GET().build();

            HttpResponse<String> resp = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                log.debug("Yahoo Finance {} → HTTP {}", symbol, resp.statusCode());
                return null;
            }

            JsonNode meta = MAPPER.readTree(resp.body())
                    .path("chart").path("result").path(0).path("meta");
            if (meta.isMissingNode()) return null;

            double price    = meta.path("regularMarketPrice").asDouble(0);
            // 전 거래일 종가 기준(오늘 등락률). previousClose 우선, 없으면 chartPreviousClose.
            // chartPreviousClose는 range(2d) 시작 '이전' 종가라 2일치 등락이 계산돼 부호가 뒤집혔음.
            double prevClose = meta.path("previousClose").asDouble(0);
            if (prevClose == 0) prevClose = meta.path("chartPreviousClose").asDouble(0);
            double change   = prevClose != 0 ? price - prevClose : 0;
            double changePct = prevClose != 0 ? change / prevClose * 100 : 0;
            String currency = meta.path("currency").asText(null);
            String state    = meta.path("marketState").asText(null);

            return new QuoteDto(symbol, name, price, change, changePct, currency, state);

        } catch (Exception e) {
            log.debug("Yahoo Finance {} 조회 실패: {}", symbol, e.getMessage());
            return null;
        }
    }
}
