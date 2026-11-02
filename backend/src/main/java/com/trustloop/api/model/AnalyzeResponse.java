package com.trustloop.api.model;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

public record AnalyzeResponse(String requestId, List<AnalyzeResult> results) {

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record AnalyzeResult(
            String reviewKey,
            String status,
            Integer trustScore,
            String verdict,
            String evidenceQuality,
            String reasonCode,
            List<Signal> signals,
            String modelVersion,
            String engine) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Signal(String kind, String summary, Double contribution) {
    }
}
