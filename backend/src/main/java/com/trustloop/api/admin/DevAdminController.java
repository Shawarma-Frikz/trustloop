package com.trustloop.api.admin;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.context.annotation.Profile;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@Profile("dev-admin")
@RequestMapping("/api/v1/admin")
public class DevAdminController {
    private final AdapterInspectionService adapters;
    private final DevMetrics metrics;

    public DevAdminController(AdapterInspectionService adapters, DevMetrics metrics) {
        this.adapters = adapters;
        this.metrics = metrics;
    }

    @GetMapping(produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> dashboard() throws IOException {
        String html = new String(new ClassPathResource("dev-admin.html").getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore())
                .header("X-Content-Type-Options", "nosniff")
                .header("Content-Security-Policy",
                        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
                .contentType(MediaType.TEXT_HTML).body(html);
    }

    @GetMapping("/adapters")
    public Map<String, List<Map<String, Object>>> adapters() {
        return Map.of("adapters", adapters.adapters());
    }

    @GetMapping("/adapters/{adapterId}/fixtures")
    public Map<String, List<Map<String, Object>>> fixtures(@PathVariable String adapterId) {
        return Map.of("fixtures", adapters.fixtures(adapterId));
    }

    @GetMapping(value = "/adapters/{adapterId}/fixtures/{fixtureName}", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> fixture(@PathVariable String adapterId, @PathVariable String fixtureName) throws IOException {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).contentType(MediaType.TEXT_HTML)
                .header("X-Content-Type-Options", "nosniff")
                .header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; script-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
                .body(adapters.fixtureHtml(adapterId, fixtureName));
    }

    @PutMapping("/adapters/{adapterId}/enabled")
    public Map<String, Object> setEnabled(@PathVariable String adapterId, @Valid @RequestBody ToggleRequest request) {
        return adapters.setEnabled(adapterId, request.enabled());
    }

    @GetMapping("/metrics")
    public Map<String, Object> metrics() {
        return metrics.snapshot();
    }

    public record ToggleRequest(@NotNull Boolean enabled) {}
}
