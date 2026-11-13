package com.trustloop.api.admin;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Local-only adapter catalog and volatile enable switches; deliberately has no persistence. */
@Service
@Profile("dev-admin")
public class AdapterInspectionService {
    private static final String MANIFEST_RESOURCE = "inspection/adapters/amazon-reviews.v1.json";
    private final JsonNode manifest;
    private final Map<String, Boolean> enabled = new ConcurrentHashMap<>();

    public AdapterInspectionService(ObjectMapper mapper) {
        try (InputStream stream = new ClassPathResource(MANIFEST_RESOURCE).getInputStream()) {
            this.manifest = mapper.readTree(stream);
            enabled.put(manifest.path("id").asText(), true);
        } catch (IOException exception) {
            throw new IllegalStateException("Could not load bundled adapter inspection manifest", exception);
        }
    }

    public List<Map<String, Object>> adapters() {
        List<Map<String, Object>> result = new ArrayList<>();
        Map<String, Object> adapter = new HashMap<>();
        adapter.put("id", manifest.path("id").asText());
        adapter.put("version", manifest.path("version").asText());
        adapter.put("description", manifest.path("description").asText());
        adapter.put("supportedPages", strings(manifest.path("supportedPages")));
        adapter.put("selectors", Map.of(
                "cards", strings(manifest.path("cardSelectors")),
                "reviewBodies", strings(manifest.path("bodySelectors"))));
        adapter.put("eligibility", manifest.path("eligibility"));
        adapter.put("enabled", enabled.getOrDefault(manifest.path("id").asText(), false));
        adapter.put("fixtures", fixtures(manifest.path("id").asText()));
        result.add(Map.copyOf(adapter));
        return List.copyOf(result);
    }

    public List<Map<String, Object>> fixtures(String adapterId) {
        requireAdapter(adapterId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (JsonNode fixture : manifest.path("fixtures").path("supported")) {
            result.add(fixtureView(fixture.asText(), true));
        }
        result.add(fixtureView(manifest.path("fixtures").path("unsupported").asText(), false));
        return List.copyOf(result);
    }

    public Map<String, Object> setEnabled(String adapterId, boolean value) {
        requireAdapter(adapterId);
        enabled.put(adapterId, value);
        return Map.of("id", adapterId, "enabled", value);
    }

    public String fixtureHtml(String adapterId, String fixtureName) {
        requireAdapter(adapterId);
        Map<String, String> approvedFixtures = new HashMap<>();
        for (Map<String, Object> fixture : fixtures(adapterId)) {
            approvedFixtures.put((String) fixture.get("name"), (String) fixture.get("resource"));
        }
        String resourceName = approvedFixtures.get(fixtureName);
        if (resourceName == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        try (InputStream stream = new ClassPathResource(resourceName).getInputStream()) {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }
    }

    private Map<String, Object> fixtureView(String path, boolean supported) {
        String name = path.substring(path.lastIndexOf('/') + 1).replaceFirst("\\.html$", "");
        String resource = "inspection/fixtures/amazon/" + name + ".html";
        return Map.of(
                "name", name,
                "supportedFixture", supported,
                "expectedState", supported ? "READY" : "UNSUPPORTED_PAGE",
                "resource", resource);
    }

    private void requireAdapter(String adapterId) {
        if (!manifest.path("id").asText().equals(adapterId)) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    }

    private List<String> strings(JsonNode node) {
        List<String> values = new ArrayList<>();
        node.forEach(value -> values.add(value.asText()));
        return List.copyOf(values);
    }
}
