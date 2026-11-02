package com.trustloop.api.controllers;

import com.trustloop.api.services.ScoringClient;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class HealthController {
    private final ScoringClient scoringClient;

    public HealthController(ScoringClient scoringClient) {
        this.scoringClient = scoringClient;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        boolean ready = scoringClient.ready();
        return ResponseEntity.status(ready ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("status", ready ? "ready" : "not_ready"));
    }
}
