package com.trustloop.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.config.ScoringProperties;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.services.HttpScoringClient;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;
import org.springframework.http.HttpStatus;

class HttpScoringClientTests {
    private static final String SCORE_RESPONSE = """
            {"results":[{"reviewKey":"review-1","status":"UNKNOWN",
            "reasonCode":"SCORING_UNAVAILABLE","signals":[],
            "modelVersion":"tl-text-1.1.0","engine":"MODEL"}]}
            """;

    @Test
    void sendsTheInternalBatchWithTokenAndRequestIdThenParsesResponse() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        HttpScoringClient client = new HttpScoringClient(
                builder.build(), new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0"),
                new ObjectMapper());
        ScoreRequest request = new ScoreRequest(List.of(
                new ScoreRequest.Review("review-1", "A long enough review text for forwarding.", true)));

        server.expect(requestTo("http://scoring.test/score"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Internal-Token", "local-token"))
                .andExpect(header("X-Request-Id", "request-42"))
                .andExpect(content().json("""
                        {"reviews":[{"reviewKey":"review-1","text":"A long enough review text for forwarding.","batchDuplicate":true}]}
                        """))
                .andRespond(withSuccess(SCORE_RESPONSE, MediaType.APPLICATION_JSON));

        var response = client.score(request, "request-42");

        assertEquals("review-1", response.results().getFirst().reviewKey());
        assertEquals("UNKNOWN", response.results().getFirst().status());
        assertEquals("SCORING_UNAVAILABLE", response.results().getFirst().reasonCode());
        server.verify();
    }

    @Test
    void healthRequiresAReadyScoringResponse() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        HttpScoringClient client = new HttpScoringClient(
                builder.build(), new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0"),
                new ObjectMapper());
        server.expect(requestTo("http://scoring.test/health"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("{\"status\":\"ready\"}", MediaType.APPLICATION_JSON));
        assertTrue(client.ready());
        server.verify();

        RestClient.Builder unavailableBuilder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer unavailableServer = MockRestServiceServer.bindTo(unavailableBuilder).build();
        HttpScoringClient unavailableClient = new HttpScoringClient(
                unavailableBuilder.build(), new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0"),
                new ObjectMapper());
        unavailableServer.expect(requestTo("http://scoring.test/health"))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));
        assertFalse(unavailableClient.ready());
        unavailableServer.verify();
    }
}
