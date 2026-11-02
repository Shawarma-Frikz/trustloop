package com.trustloop.api.controllers;

import com.trustloop.api.config.ScoringProperties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class VersionController {
    private final ScoringProperties scoringProperties;
    private final String version;

    public VersionController(
            ScoringProperties scoringProperties,
            @Value("${spring.application.version:0.0.1-SNAPSHOT}") String version) {
        this.scoringProperties = scoringProperties;
        this.version = version;
    }

    @GetMapping("/version")
    public VersionResponse version() {
        return new VersionResponse("trustloop-api", version, "v1",
                scoringProperties.expectedModelVersion(), "MODEL");
    }

    public record VersionResponse(
            String service,
            String version,
            String contractVersion,
            String expectedModelVersion,
            String engine) {
    }
}
