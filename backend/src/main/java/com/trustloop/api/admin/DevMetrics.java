package com.trustloop.api.admin;

import com.trustloop.api.model.AnalyzeResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;
import java.util.regex.Pattern;

/** Volatile aggregates with fixed labels; never retains a request or review field. */
@Component
@Profile("dev-admin")
public class DevMetrics {
    private static final Set<String> RESULT_STATUSES = Set.of("SCORED", "SIGNALS_ONLY", "UNKNOWN", "OTHER");
    private static final Set<String> REASON_CODES = Set.of(
            "INSUFFICIENT_TEXT", "UNSUPPORTED_LANGUAGE", "SCORING_TIMEOUT", "SCORING_UNAVAILABLE",
            "INVALID_REQUEST", "PAYLOAD_TOO_LARGE", "RATE_LIMITED", "INTERNAL_ERROR", "NONE", "OTHER");
    private static final Set<String> ENGINES = Set.of("MODEL", "SIGNALS_ONLY", "OTHER");
    private static final Pattern MODEL_VERSION = Pattern.compile("^tl-text-\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$");
    private static final String[] LATENCY_BUCKETS = {
            "le_10_ms", "le_50_ms", "le_100_ms", "le_250_ms", "le_500_ms", "le_1000_ms", "gt_1000_ms"
    };
    private final LongAdder totalRequests = new LongAdder();
    private final Map<Integer, LongAdder> httpStatusCounts = new ConcurrentHashMap<>();
    private final Map<String, LongAdder> resultStatusCounts = counters(RESULT_STATUSES);
    private final Map<String, LongAdder> reasonCodeCounts = counters(REASON_CODES);
    private final Map<String, LongAdder> engineCounts = counters(ENGINES);
    private final Map<String, LongAdder> modelVersionCounts = new ConcurrentHashMap<>();
    private final LongAdder[] latencyCounts = new LongAdder[LATENCY_BUCKETS.length];
    private final String expectedModelVersion;

    public DevMetrics(@Value("${trustloop.scoring.expected-model-version:}") String configuredModelVersion) {
        expectedModelVersion = configuredModelVersion != null
                && MODEL_VERSION.matcher(configuredModelVersion).matches() ? configuredModelVersion : "OTHER";
        modelVersionCounts.put(expectedModelVersion, new LongAdder());
        modelVersionCounts.put("NOT_APPLICABLE", new LongAdder());
        modelVersionCounts.put("OTHER", new LongAdder());
        for (int index = 0; index < latencyCounts.length; index++) latencyCounts[index] = new LongAdder();
    }

    private static Map<String, LongAdder> counters(Set<String> labels) {
        Map<String, LongAdder> result = new ConcurrentHashMap<>();
        labels.forEach(label -> result.put(label, new LongAdder()));
        return result;
    }

    public void record(long elapsedNanos, int status) {
        totalRequests.increment();
        httpStatusCounts.computeIfAbsent(status, ignored -> new LongAdder()).increment();
        double millis = elapsedNanos / 1_000_000.0;
        double[] upperBounds = {10, 50, 100, 250, 500, 1000};
        int bucket = upperBounds.length;
        for (int index = 0; index < upperBounds.length; index++) {
            if (millis <= upperBounds[index]) { bucket = index; break; }
        }
        latencyCounts[bucket].increment();
    }

    /** Only fixed enum labels and the configured model version are retained. */
    public void recordResults(List<AnalyzeResponse.AnalyzeResult> results) {
        if (results == null) return;
        for (AnalyzeResponse.AnalyzeResult result : results) {
            if (result == null) continue;
            increment(resultStatusCounts, result.status(), "OTHER");
            increment(reasonCodeCounts, result.reasonCode(), "NONE");
            increment(engineCounts, result.engine(), "OTHER");
            incrementModelVersion(result.modelVersion());
        }
    }

    /** Request-level error codes use the same fixed reason-code vocabulary. */
    public void recordReasonCode(String reasonCode) {
        increment(reasonCodeCounts, reasonCode, "OTHER");
    }

    private static void increment(Map<String, LongAdder> counters, String candidate, String nullLabel) {
        String label = candidate == null ? nullLabel : candidate;
        LongAdder counter = counters.get(label);
        (counter == null ? counters.get("OTHER") : counter).increment();
    }

    private void incrementModelVersion(String candidate) {
        String label = candidate == null ? "NOT_APPLICABLE"
                : expectedModelVersion.equals(candidate) ? expectedModelVersion : "OTHER";
        modelVersionCounts.get(label).increment();
    }

    public Map<String, Object> snapshot() {
        Map<Integer, Long> httpStatuses = new LinkedHashMap<>();
        httpStatusCounts.keySet().stream().sorted().forEach(status -> httpStatuses.put(status, httpStatusCounts.get(status).sum()));
        Map<String, Long> latencies = new LinkedHashMap<>();
        for (int index = 0; index < LATENCY_BUCKETS.length; index++) {
            latencies.put(LATENCY_BUCKETS[index], latencyCounts[index].sum());
        }
        return Map.of(
                "requestCount", totalRequests.sum(),
                "httpStatusCounts", Map.copyOf(httpStatuses),
                "statusCounts", snapshot(resultStatusCounts),
                "reasonCodeCounts", snapshot(reasonCodeCounts),
                "engineCounts", snapshot(engineCounts),
                "modelVersionCounts", snapshot(modelVersionCounts),
                "latencyBuckets", Map.copyOf(latencies));
    }

    private static Map<String, Long> snapshot(Map<String, LongAdder> source) {
        Map<String, Long> result = new LinkedHashMap<>();
        source.keySet().stream().sorted().forEach(label -> result.put(label, source.get(label).sum()));
        return Map.copyOf(result);
    }
}
