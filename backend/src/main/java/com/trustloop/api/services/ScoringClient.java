package com.trustloop.api.services;

import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.model.ScoreResponse;

public interface ScoringClient {
    ScoreResponse score(ScoreRequest request, String requestId);

    boolean ready();
}
