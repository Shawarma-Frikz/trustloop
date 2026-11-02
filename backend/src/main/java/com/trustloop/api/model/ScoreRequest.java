package com.trustloop.api.model;

import java.util.List;

public record ScoreRequest(List<Review> reviews) {
    public record Review(String reviewKey, String text, boolean batchDuplicate) {
    }
}
