package com.trustloop.api.admin;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;

/** Volatile counters with fixed buckets and no request-derived labels or values. */
@Component
@Profile("dev-admin")
public class DevMetrics {
    private static final String[] LATENCY_BUCKETS = {
            "le_10_ms", "le_50_ms", "le_100_ms", "le_250_ms", "le_500_ms", "le_1000_ms", "gt_1000_ms"
    };
    private final LongAdder totalRequests = new LongAdder();
    private final Map<Integer, LongAdder> statusCounts = new ConcurrentHashMap<>();
    private final LongAdder[] latencyCounts = new LongAdder[LATENCY_BUCKETS.length];

    public DevMetrics() {
        for (int index = 0; index < latencyCounts.length; index++) latencyCounts[index] = new LongAdder();
    }

    public void record(long elapsedNanos, int status) {
        totalRequests.increment();
        statusCounts.computeIfAbsent(status, ignored -> new LongAdder()).increment();
        double millis = elapsedNanos / 1_000_000.0;
        double[] upperBounds = {10, 50, 100, 250, 500, 1000};
        int bucket = upperBounds.length;
        for (int index = 0; index < upperBounds.length; index++) {
            if (millis <= upperBounds[index]) { bucket = index; break; }
        }
        latencyCounts[bucket].increment();
    }

    public Map<String, Object> snapshot() {
        Map<Integer, Long> statuses = new LinkedHashMap<>();
        statusCounts.keySet().stream().sorted().forEach(status -> statuses.put(status, statusCounts.get(status).sum()));
        Map<String, Long> latencies = new LinkedHashMap<>();
        for (int index = 0; index < LATENCY_BUCKETS.length; index++) {
            latencies.put(LATENCY_BUCKETS[index], latencyCounts[index].sum());
        }
        return Map.of("requestCount", totalRequests.sum(), "statusCounts", Map.copyOf(statuses), "latencyBuckets", Map.copyOf(latencies));
    }
}
