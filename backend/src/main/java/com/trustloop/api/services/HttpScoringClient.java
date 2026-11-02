package com.trustloop.api.services;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.config.ScoringProperties;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.model.ScoreResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class HttpScoringClient implements ScoringClient {
    private final RestClient restClient;
    private final ScoringProperties properties;
    private final ObjectMapper strictMapper;

    public HttpScoringClient(RestClient scoringRestClient, ScoringProperties properties, ObjectMapper mapper) {
        this.restClient = scoringRestClient;
        this.properties = properties;
        this.strictMapper = mapper.copy().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
    }

    @Override
    public ScoreResponse score(ScoreRequest request, String requestId) {
        if (properties.token() == null || properties.token().isBlank()) {
            throw new ScoringUnavailableException("scoring token is not configured");
        }
        String body = restClient.post()
                .uri("/score")
                .header("X-Internal-Token", properties.token())
                .header("X-Request-Id", requestId)
                .body(request)
                .retrieve()
                .body(String.class);
        try {
            return strictMapper.readValue(body, ScoreResponse.class);
        } catch (JsonProcessingException exception) {
            throw new ScoringUnavailableException("scoring response does not match contract v1", exception);
        }
    }

    @Override
    public boolean ready() {
        try {
            String body = restClient.get().uri("/health").retrieve().body(String.class);
            var response = strictMapper.readTree(body);
            return response.size() == 1 && "ready".equals(response.path("status").asText());
        } catch (Exception exception) {
            return false;
        }
    }
}
