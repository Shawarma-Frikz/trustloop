package com.trustloop.api.admin;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.model.ScoreResponse;
import com.trustloop.api.TrustLoopApiApplication;
import com.trustloop.api.services.ScoringClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import org.springframework.http.MediaType;

@SpringBootTest(properties = {
        "trustloop.api.rate-limit-per-minute=100"
})
@ActiveProfiles("dev-admin")
@AutoConfigureMockMvc
@Import(DevAdminTests.ScoringStubConfiguration.class)
class DevAdminTests {
    private static final String ADAPTER_ID = "amazon.reviews.v1";

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @Autowired Environment environment;

    @Test
    void developmentAdminProfilePinsLoopbackAndRequiresLocalOnlyFlag() {
        assertEquals("127.0.0.1", environment.getProperty("server.address"));
        assertEquals("true", environment.getProperty("app.admin.local-only"));
    }

    @Test
    void localDashboardListsAdapterAndExplainsItsDevelopmentOnlyScope() throws Exception {
        mockMvc.perform(get("/api/v1/admin"))
                .andExpect(status().isOk())
                .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("no-store")))
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_HTML))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("Development-only view")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("do not change extension scanning")));

        mockMvc.perform(get("/api/v1/admin/adapters"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.adapters[0].id").value(ADAPTER_ID))
                .andExpect(jsonPath("$.adapters[0].version").value("1.0.0"))
                .andExpect(jsonPath("$.adapters[0].supportedPages.length()").value(4))
                .andExpect(jsonPath("$.adapters[0].fixtures.length()").value(5));
    }

    @Test
    void fixturesAreInspectableAndListingThemDoesNotChangeToggleState() throws Exception {
        mockMvc.perform(get("/api/v1/admin/adapters/{id}/fixtures", ADAPTER_ID))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.fixtures[0].expectedState").value("READY"))
                .andExpect(jsonPath("$.fixtures[4].expectedState").value("UNSUPPORTED_PAGE"));

        mockMvc.perform(get("/api/v1/admin/adapters/{id}/fixtures/{name}", ADAPTER_ID, "standard"))
                .andExpect(status().isOk())
                .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("no-store")))
                .andExpect(header().string("Content-Security-Policy", org.hamcrest.Matchers.containsString("frame-ancestors 'self'")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("data-fixture-source=\"synthetic\"")));

        mockMvc.perform(get("/api/v1/admin/adapters"))
                .andExpect(jsonPath("$.adapters[0].enabled").value(true));
    }

    @Test
    void toggleIsVolatileAndUnknownAdaptersOrFixturesAreNotExposed() throws Exception {
        mockMvc.perform(put("/api/v1/admin/adapters/{id}/enabled", ADAPTER_ID)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"enabled\":false}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.enabled").value(false));
        mockMvc.perform(get("/api/v1/admin/adapters"))
                .andExpect(jsonPath("$.adapters[0].enabled").value(false));
        mockMvc.perform(get("/api/v1/admin/adapters/{id}/fixtures/{name}", ADAPTER_ID, "../../application"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/api/v1/admin/adapters/{id}/fixtures/{name}", ADAPTER_ID, "unknown-fixture"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/api/v1/admin/adapters/{id}/fixtures", "unbundled.adapter"))
                .andExpect(status().isNotFound());
    }

    @Test
    void metricsContainOnlyCountsStatusesAndFixedLatencyBuckets() throws Exception {
        mockMvc.perform(post("/api/v1/analyze")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"adapterId":"amazon.reviews.v1","languageHint":"en","reviews":[
                                  {"reviewKey":"private-key-sentinel","text":"private-text-sentinel I have used this product every morning for several weeks and it still works well."}
                                ]}
                                """))
                .andExpect(status().isOk());

        var result = mockMvc.perform(get("/api/v1/admin/metrics"))
                .andExpect(status().isOk())
                .andReturn();
        String body = result.getResponse().getContentAsString();
        JsonNode metrics = objectMapper.readTree(body);
        assertTrue(metrics.path("requestCount").asLong() >= 1);
        assertTrue(metrics.path("statusCounts").path("200").asLong() >= 1);
        assertEquals(7, metrics.path("latencyBuckets").size());
        for (String forbidden : List.of("private-key-sentinel", "private-text-sentinel", "reviewKey", "hostname", "url")) {
            assertFalse(body.toLowerCase().contains(forbidden.toLowerCase()));
        }
    }

    @Test
    void loopbackGuardRejectsAnyNonLoopbackBind() {
        new DevAdminLoopbackGuard("127.0.0.1", true).requireLoopback();
        new DevAdminLoopbackGuard("::1", true).requireLoopback();
        assertThrows(IllegalStateException.class, () -> new DevAdminLoopbackGuard("0.0.0.0", true).requireLoopback());
        assertThrows(IllegalStateException.class, () -> new DevAdminLoopbackGuard("192.168.1.20", true).requireLoopback());
        assertThrows(IllegalStateException.class, () -> new DevAdminLoopbackGuard("127.0.0.1", false).requireLoopback());
    }

    @Test
    void springApplicationStartupFailsWhenDevAdminIsConfiguredForANonLoopbackAddress() {
        RuntimeException failure = assertThrows(RuntimeException.class, () -> {
            try (ConfigurableApplicationContext ignored = new SpringApplicationBuilder(TrustLoopApiApplication.class)
                    .web(WebApplicationType.NONE)
                    .profiles("dev-admin")
                    .run(
                            "--server.address=0.0.0.0",
                            "--app.admin.local-only=true",
                            "--spring.main.banner-mode=off",
                            "--spring.main.log-startup-info=false",
                            "--logging.level.root=OFF")) {
                throw new AssertionError("Application started with a non-loopback dev-admin bind.");
            }
        });

        Throwable cause = failure;
        boolean guardRejectedStartup = false;
        while (cause != null) {
            if (cause instanceof IllegalStateException
                    && cause.getMessage() != null
                    && cause.getMessage().contains("loopback server.address")) {
                guardRejectedStartup = true;
                break;
            }
            cause = cause.getCause();
        }
        assertTrue(guardRejectedStartup, "startup must fail specifically because the admin bind is not loopback");
    }

    @TestConfiguration
    static class ScoringStubConfiguration {
        @Bean @Primary
        ScoringClient scoringClient() {
            return new ScoringClient() {
                @Override public ScoreResponse score(ScoreRequest request, String requestId) {
                    return new ScoreResponse(request.reviews().stream().map(review ->
                            new ScoreResponse.Result(review.reviewKey(), "UNKNOWN", null, null, null,
                                    null, "SCORING_UNAVAILABLE", List.of(), "tl-text-1.1.0", "MODEL")).toList());
                }
                @Override public boolean ready() { return true; }
            };
        }
    }
}
