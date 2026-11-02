package com.trustloop.api.model;

import java.util.List;

public record ScoreResponse(List<Result> results) {
    public record Result(
            String reviewKey,
            String status,
            Integer trustScore,
            Double pOrganic,
            String verdict,
            String evidenceQuality,
            String reasonCode,
            List<Signal> signals,
            String modelVersion,
            String engine) {
    }

    public record Signal(String kind, String summary, Double contribution) {
    }
}
