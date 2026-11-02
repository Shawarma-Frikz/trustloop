package com.trustloop.api.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.Collections;
import java.util.NavigableMap;
import java.util.TreeMap;

@Component
public class ContractValues {
    private final NavigableMap<Integer, String> verdictBands;
    private final int maxRequestBytes;
    private final int rateLimitPerMinute;
    private final String requestIdHeader;

    public ContractValues(ObjectMapper mapper) {
        try {
            JsonNode root = mapper.readTree(new ClassPathResource("contracts/v1/constants.json").getInputStream());
            TreeMap<Integer, String> bands = new TreeMap<>();
            root.path("bands").forEach(band -> bands.put(band.path("min").asInt(), band.path("name").asText()));
            if (bands.isEmpty()) {
                throw new IllegalStateException("contract v1 has no verdict bands");
            }
            verdictBands = Collections.unmodifiableNavigableMap(bands);
            JsonNode constants = root.path("constants");
            maxRequestBytes = constants.path("MAX_REQUEST_BYTES").asInt();
            rateLimitPerMinute = constants.path("RATE_LIMIT_PER_MINUTE").asInt();
            requestIdHeader = constants.path("REQUEST_ID_HEADER").asText();
            if (maxRequestBytes < 1 || rateLimitPerMinute < 1 || requestIdHeader.isBlank()) {
                throw new IllegalStateException("contract v1 runtime limits are invalid");
            }
        } catch (IOException exception) {
            throw new UncheckedIOException("cannot load contract v1 constants", exception);
        }
    }

    public String verdictFor(int trustScore) {
        var band = verdictBands.floorEntry(trustScore);
        return band == null ? null : band.getValue();
    }

    public int maxRequestBytes() {
        return maxRequestBytes;
    }

    public int rateLimitPerMinute() {
        return rateLimitPerMinute;
    }

    public String requestIdHeader() {
        return requestIdHeader;
    }
}
