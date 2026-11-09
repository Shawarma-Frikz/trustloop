package com.trustloop.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.config.ScoringProperties;
import com.trustloop.api.model.AnalyzeRequest;
import com.trustloop.api.model.AnalyzeResponse;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.services.HttpScoringClient;
import com.trustloop.api.services.AnalyzeService;
import com.trustloop.api.services.ContractValues;
import com.trustloop.api.services.ScoringUnavailableException;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertThrows;
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

    @Test
    void malformedJsonIsRejectedAsAnUnavailableScoringResponse() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        HttpScoringClient client = new HttpScoringClient(
                builder.build(), new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0"),
                new ObjectMapper());
        server.expect(requestTo("http://scoring.test/score"))
                .andRespond(withSuccess("{not-json", MediaType.APPLICATION_JSON));

        assertThrows(ScoringUnavailableException.class, () -> client.score(
                new ScoreRequest(List.of(new ScoreRequest.Review("review-1", "long enough text", false))),
                "request-bad-json"));
        server.verify();
    }

    @Test
    void malformedJsonProducesUnknownForEveryReviewInTheBatch() {
        AnalyzeResponse response = analyzeBatchWithFailure(
                withSuccess("{not-json", MediaType.APPLICATION_JSON));
        assertUnknownForWholeBatch(response, "SCORING_UNAVAILABLE");
    }

    @Test
    void non2xxScoringResponseIsRejectedInsteadOfParsedAsAScore() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        HttpScoringClient client = new HttpScoringClient(
                builder.build(), new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0"),
                new ObjectMapper());
        server.expect(requestTo("http://scoring.test/score"))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));

        assertThrows(RestClientResponseException.class, () -> client.score(
                new ScoreRequest(List.of(new ScoreRequest.Review("review-1", "long enough text", false))),
                "request-server-error"));
        server.verify();
    }

    @Test
    void serverErrorProducesUnknownForEveryReviewInTheBatch() {
        AnalyzeResponse response = analyzeBatchWithFailure(
                withStatus(HttpStatus.INTERNAL_SERVER_ERROR));
        assertUnknownForWholeBatch(response, "SCORING_UNAVAILABLE");
    }

    private AnalyzeResponse analyzeBatchWithFailure(
            org.springframework.test.web.client.ResponseCreator failureResponse) {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://scoring.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://scoring.test/score")).andRespond(failureResponse);
        ScoringProperties properties = new ScoringProperties("http://scoring.test", "local-token", "tl-text-1.1.0");
        ObjectMapper mapper = new ObjectMapper();
        AnalyzeService service = new AnalyzeService(
                new HttpScoringClient(builder.build(), properties, mapper), properties, new ContractValues(mapper));
        AnalyzeRequest request = new AnalyzeRequest("amazon.reviews.v1", "en", List.of(
                new AnalyzeRequest.AnalyzeReview("review-1", "A first review with enough text for the scoring path."),
                new AnalyzeRequest.AnalyzeReview("review-2", "A second review with enough text for the scoring path.")));

        AnalyzeResponse response = service.analyze(request, "request-failure-test");
        server.verify();
        return response;
    }

    private void assertUnknownForWholeBatch(AnalyzeResponse response, String expectedReason) {
        assertEquals(2, response.results().size());
        response.results().forEach(result -> {
            assertEquals("UNKNOWN", result.status());
            assertEquals(expectedReason, result.reasonCode());
            assertEquals(null, result.trustScore());
            assertEquals(null, result.verdict());
        });
    }
}
