package com.trustloop.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.model.ScoreResponse;
import com.trustloop.api.services.ScoringClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.web.client.ResourceAccessException;

import java.net.ConnectException;
import java.net.SocketTimeoutException;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "trustloop.allowed-origins=chrome-extension://trustloop-test",
        "trustloop.api.rate-limit-per-minute=2"
})
@AutoConfigureMockMvc
@Import(PublicApiTests.StubConfiguration.class)
class PublicApiTests {
    private static final String REQUEST_ID = "api-test-123";
    private static final String VALID_REQUEST = """
            {"adapterId":"amazon.reviews.v1","languageHint":"en","reviews":[
              {"reviewKey":"review-1","text":"I have used this product every morning for several weeks and the battery still lasts through my commute."}
            ]}
            """;

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private StubScoringClient scoringClient;

    @BeforeEach
    void scoringServiceIsReady() {
        scoringClient.setReady(true);
        scoringClient.setResponse(unknownResponse());
        scoringClient.setFailure(null);
    }

    @Test
    void analyzeMapsValidScoreAndDoesNotExposeInternalProbability() throws Exception {
        scoringClient.setResponse(new ScoreResponse(List.of(
                new ScoreResponse.Result("review-1", "SCORED", 73, 0.731,
                        "LIKELY_ORGANIC", "ADEQUATE", null,
                        List.of(new ScoreResponse.Signal("CONCRETE_DETAIL", "Includes a concrete usage detail", 0.18)),
                        "tl-text-1.1.0", "MODEL"))));

        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.20"))
                        .header("X-Request-Id", REQUEST_ID)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(VALID_REQUEST))
                .andExpect(status().isOk())
                .andExpect(header().string("X-Request-Id", REQUEST_ID))
                .andReturn();

        JsonNode response = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        assertEquals(REQUEST_ID, response.path("requestId").asText());
        assertEquals("SCORED", response.at("/results/0/status").asText());
        assertEquals(73, response.at("/results/0/trustScore").asInt());
        assertFalse(response.at("/results/0").has("pOrganic"));
        assertEquals(REQUEST_ID, scoringClient.lastRequestId());
        assertEquals("review-1", scoringClient.lastRequest().reviews().getFirst().reviewKey());
    }

    @Test
    void invalidRequestsUseTheSafeErrorEnvelopeAndRequestId() throws Exception {
        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.21"))
                        .header("X-Request-Id", REQUEST_ID)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"adapterId\":\"amazon.reviews.v1\",\"reviews\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(header().string("X-Request-Id", REQUEST_ID))
                .andReturn();

        JsonNode error = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        assertEquals(REQUEST_ID, error.path("requestId").asText());
        assertEquals("INVALID_REQUEST", error.at("/error/code").asText());
        assertEquals("Request rejected.", error.at("/error/message").asText());
    }

    @Test
    void malformedAndOversizedRequestsUseContractErrorEnvelope() throws Exception {
        MvcResult malformed = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.22"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{bad json"))
                .andExpect(status().isBadRequest()).andReturn();
        JsonNode malformedError = objectMapper.readTree(malformed.getResponse().getContentAsByteArray());
        assertEquals("INVALID_REQUEST", malformedError.at("/error/code").asText());
        assertTrue(malformedError.path("requestId").isTextual());

        String oversizedBody = "x".repeat(131_073);
        MvcResult oversized = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.23"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(oversizedBody))
                .andExpect(status().isPayloadTooLarge()).andReturn();
        JsonNode oversizedError = objectMapper.readTree(oversized.getResponse().getContentAsByteArray());
        assertEquals("PAYLOAD_TOO_LARGE", oversizedError.at("/error/code").asText());
    }

    @Test
    void invalidRequestIdIsReplacedAndRejectedSafely() throws Exception {
        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .header("X-Request-Id", "bad request id")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(VALID_REQUEST))
                .andExpect(status().isBadRequest())
                .andReturn();
        JsonNode error = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        String generatedId = result.getResponse().getHeader("X-Request-Id");
        assertTrue(generatedId != null && generatedId.matches("^[A-Za-z0-9-]{1,64}$"));
        assertEquals(generatedId, error.path("requestId").asText());
        assertEquals("INVALID_REQUEST", error.at("/error/code").asText());
    }

    @Test
    void inconsistentScoringResponseFailsClosedWithoutLeakingScore() throws Exception {
        scoringClient.setResponse(new ScoreResponse(List.of(
                new ScoreResponse.Result("review-1", "SCORED", 50, 0.731,
                        "INCONCLUSIVE", "ADEQUATE", null, List.of(), "tl-text-1.1.0", "MODEL"))));

        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.24"))
                        .header("X-Request-Id", REQUEST_ID)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(VALID_REQUEST))
                .andExpect(status().isOk()).andReturn();
        JsonNode output = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        assertEquals("UNKNOWN", output.at("/results/0/status").asText());
        assertEquals("SCORING_UNAVAILABLE", output.at("/results/0/reasonCode").asText());
        assertFalse(output.at("/results/0").has("trustScore"));
    }

    @Test
    void modelVersionMismatchFailsClosedForTheEntireBatch() throws Exception {
        scoringClient.setResponse(new ScoreResponse(List.of(
                new ScoreResponse.Result("review-1", "SCORED", 73, 0.731,
                        "LIKELY_ORGANIC", "ADEQUATE", null, List.of(), "tl-text-1.1.0", "MODEL"),
                new ScoreResponse.Result("review-2", "SCORED", 73, 0.731,
                        "LIKELY_ORGANIC", "ADEQUATE", null, List.of(), "tl-text-9.9.9", "MODEL"))));
        String batch = """
                {"adapterId":"amazon.reviews.v1","languageHint":"en","reviews":[
                  {"reviewKey":"review-1","text":"Review text long enough for the analyzer to accept and forward to the scoring service."},
                  {"reviewKey":"review-2","text":"Another review text long enough for this batch request to meet minimum length."}
                ]}
                """;

        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.33"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(batch))
                .andExpect(status().isOk()).andReturn();
        JsonNode results = objectMapper.readTree(result.getResponse().getContentAsByteArray()).path("results");

        assertEquals(2, results.size());
        for (JsonNode item : results) {
            assertEquals("UNKNOWN", item.path("status").asText());
            assertEquals("SCORING_UNAVAILABLE", item.path("reasonCode").asText());
            assertFalse(item.has("trustScore"));
        }
    }

    @Test
    void scoringTimeoutMarksEveryReviewUnknownWithTimeoutReason() throws Exception {
        scoringClient.setFailure(new ResourceAccessException("read timed out", new SocketTimeoutException()));
        String batch = """
                {"adapterId":"amazon.reviews.v1","languageHint":"en","reviews":[
                  {"reviewKey":"review-1","text":"Review text long enough for the analyzer to accept and forward to the scoring service."},
                  {"reviewKey":"review-2","text":"Another review text long enough for this batch request to meet minimum length."}
                ]}
                """;
        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.31"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(batch))
                .andExpect(status().isOk()).andReturn();

        JsonNode results = objectMapper.readTree(result.getResponse().getContentAsByteArray()).path("results");
        assertEquals(2, results.size());
        for (JsonNode item : results) {
            assertEquals("UNKNOWN", item.path("status").asText());
            assertEquals("SCORING_TIMEOUT", item.path("reasonCode").asText());
            assertFalse(item.has("trustScore"));
            assertFalse(item.has("verdict"));
        }
    }

    @Test
    void connectionRefusedMarksEveryReviewUnknownAsUnavailable() throws Exception {
        scoringClient.setFailure(new ResourceAccessException("connection refused", new ConnectException()));
        String batch = """
                {"adapterId":"amazon.reviews.v1","languageHint":"en","reviews":[
                  {"reviewKey":"review-1","text":"Review text long enough for the analyzer to accept and forward to the scoring service."},
                  {"reviewKey":"review-2","text":"Another review text long enough for this batch request to meet minimum length."}
                ]}
                """;
        MvcResult result = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.32"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(batch))
                .andExpect(status().isOk()).andReturn();

        JsonNode results = objectMapper.readTree(result.getResponse().getContentAsByteArray()).path("results");
        assertEquals(2, results.size());
        for (JsonNode item : results) {
            assertEquals("UNKNOWN", item.path("status").asText());
            assertEquals("SCORING_UNAVAILABLE", item.path("reasonCode").asText());
            assertFalse(item.has("trustScore"));
        }
    }

    @Test
    void localRateLimitReturnsARequestIdAndSafeError() throws Exception {
        scoringClient.setResponse(unknownResponse());
        for (int index = 0; index < 2; index++) {
            mockMvc.perform(post("/api/v1/analyze")
                            .with(remote("192.0.2.15"))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(VALID_REQUEST))
                    .andExpect(status().isOk());
        }
        MvcResult limited = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.15"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(VALID_REQUEST))
                .andExpect(status().isTooManyRequests()).andReturn();
        JsonNode error = objectMapper.readTree(limited.getResponse().getContentAsByteArray());
        assertEquals("RATE_LIMITED", error.at("/error/code").asText());
        assertTrue(error.path("requestId").isTextual());
    }

    @Test
    void corsAllowsConfiguredExtensionAndRejectsUnknownOrigin() throws Exception {
        mockMvc.perform(options("/api/v1/analyze")
                        .header("Origin", "chrome-extension://trustloop-test")
                        .header("Access-Control-Request-Method", "POST")
                        .header("Access-Control-Request-Headers", "content-type,x-request-id"))
                .andExpect(status().isNoContent())
                .andExpect(header().string("Access-Control-Allow-Origin", "chrome-extension://trustloop-test"));

        MvcResult rejected = mockMvc.perform(post("/api/v1/analyze")
                        .with(remote("192.0.2.25"))
                        .header("Origin", "https://not-trustloop.example")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(VALID_REQUEST))
                .andExpect(status().isForbidden()).andReturn();
        JsonNode error = objectMapper.readTree(rejected.getResponse().getContentAsByteArray());
        assertEquals("INVALID_REQUEST", error.at("/error/code").asText());
    }

    @Test
    void healthAndVersionMatchTheFrozenContractShape() throws Exception {
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.status").value("ready"));
        mockMvc.perform(get("/api/v1/version"))
                .andExpect(status().isOk())
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.service").value("trustloop-api"))
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.expectedModelVersion").value("tl-text-1.1.0"));
        scoringClient.setReady(false);
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.status").value("not_ready"));
    }

    private ScoreResponse unknownResponse() {
        return new ScoreResponse(List.of(new ScoreResponse.Result("review-1", "UNKNOWN", null,
                null, null, null, "SCORING_UNAVAILABLE", List.of(), "tl-text-1.1.0", "MODEL")));
    }

    private static RequestPostProcessor remote(String address) {
        return request -> {
            request.setRemoteAddr(address);
            return request;
        };
    }

    @TestConfiguration
    static class StubConfiguration {
        @Bean
        @Primary
        StubScoringClient stubScoringClient() {
            return new StubScoringClient();
        }
    }

    static class StubScoringClient implements ScoringClient {
        private volatile boolean ready = true;
        private volatile ScoreResponse response;
        private volatile ScoreRequest lastRequest;
        private volatile String lastRequestId;
        private volatile RuntimeException failure;

        @Override
        public ScoreResponse score(ScoreRequest request, String requestId) {
            lastRequest = request;
            lastRequestId = requestId;
            if (failure != null) {
                throw failure;
            }
            return response;
        }

        @Override
        public boolean ready() {
            return ready;
        }

        void setReady(boolean ready) {
            this.ready = ready;
        }

        void setResponse(ScoreResponse response) {
            this.response = response;
        }

        void setFailure(RuntimeException failure) {
            this.failure = failure;
        }

        ScoreRequest lastRequest() {
            return lastRequest;
        }

        String lastRequestId() {
            return lastRequestId;
        }
    }
}
