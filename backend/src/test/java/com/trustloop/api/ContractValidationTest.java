package com.trustloop.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ContractValidationTest {

    private static final Path CONTRACTS = Path.of("..", "contracts", "v1");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static JsonNode read(String name) {
        try {
            return MAPPER.readTree(Files.newInputStream(CONTRACTS.resolve(name)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static JsonSchema schema(String name) {
        return JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(read(name));
    }

    private static List<String> enumValues(JsonNode enumNode) {
        List<String> values = new ArrayList<>();
        enumNode.forEach(node -> values.add(node.asText()));
        return values;
    }

    private static List<String> codesOfScope(JsonNode reasonCodes, String scope) {
        List<String> codes = new ArrayList<>();
        reasonCodes.forEach(node -> {
            if (scope.equals(node.get("scope").asText())) {
                codes.add(node.get("code").asText());
            }
        });
        return codes;
    }

    @Test
    void fixturesValidateAsTheirNamesPromise() throws IOException {
        try (Stream<Path> fixtures = Files.list(CONTRACTS.resolve("fixtures"))) {
            for (Path fixture : fixtures.filter(p -> p.getFileName().toString().endsWith(".json")).toList()) {
                String name = fixture.getFileName().toString();
                String[] segments = name.split("\\.");
                String message = segments[0];
                boolean expectValid = segments[1].startsWith("valid");
                Set<ValidationMessage> errors = schema(message + ".schema.json").validate(read("fixtures/" + name));
                if (expectValid) {
                    assertTrue(errors.isEmpty(), () -> name + " must be valid, got " + errors);
                } else {
                    assertFalse(errors.isEmpty(), name + " must be invalid but validated cleanly");
                }
            }
        }
    }

    @Test
    void schemasMatchConstants() {
        JsonNode constants = read("constants.json");
        JsonNode constantValues = constants.get("constants");

        JsonNode request = read("analyze-request.schema.json");
        assertEquals(constantValues.get("MAX_REVIEWS_PER_REQUEST").asInt(),
                request.at("/properties/reviews/maxItems").asInt());
        assertEquals(constantValues.get("MAX_REVIEW_CHARS").asInt(),
                request.at("/properties/reviews/items/properties/text/maxLength").asInt());

        JsonNode response = read("analyze-response.schema.json");
        JsonNode resultProps = response.at("/$defs/result/properties");
        assertArrayEquals(enumValues(constants.get("statuses")).toArray(),
                enumValues(resultProps.get("status").get("enum")).toArray());
        assertArrayEquals(enumValues(constants.get("engines")).toArray(),
                enumValues(resultProps.get("engine").get("enum")).toArray());
        assertArrayEquals(enumValues(constants.get("evidenceQualityLevels")).toArray(),
                enumValues(resultProps.get("evidenceQuality").get("enum")).toArray());
        assertArrayEquals(codesOfScope(constants.get("reasonCodes"), "result").toArray(),
                enumValues(resultProps.get("reasonCode").get("enum")).toArray());
        assertEquals(constantValues.get("MAX_SIGNALS").asInt(),
                resultProps.get("signals").get("maxItems").asInt());
        assertArrayEquals(signalKinds(constants).toArray(),
                enumValues(response.at("/$defs/signal/properties/kind/enum")).toArray());

        List<String> bandNames = new ArrayList<>();
        constants.get("bands").forEach(band -> bandNames.add(band.get("name").asText()));
        assertArrayEquals(bandNames.toArray(),
                enumValues(resultProps.get("verdict").get("enum")).toArray());

        JsonNode version = read("version-response.schema.json");
        assertEquals(constantValues.get("MODEL_VERSION_FORMAT").asText(),
                version.at("/properties/expectedModelVersion/pattern").asText());

        JsonNode error = read("error-response.schema.json");
        assertArrayEquals(codesOfScope(constants.get("reasonCodes"), "request_error").toArray(),
                enumValues(error.at("/properties/error/properties/code/enum")).toArray());
    }

    private static List<String> signalKinds(JsonNode constants) {
        List<String> kinds = new ArrayList<>();
        constants.get("signals").forEach(signal -> kinds.add(signal.get("kind").asText()));
        return kinds;
    }

    @Test
    void constantsAreCompleteAndCoherent() {
        JsonNode constants = read("constants.json");

        assertEquals(17, constants.get("constants").size());
        assertEquals(10, constants.get("reasonCodes").size());
        assertEquals(7, constants.get("signals").size());
        assertEquals(6, constants.get("bands").size());
        assertEquals("X-Request-Id", constants.get("constants").get("REQUEST_ID_HEADER").asText());

        JsonNode bands = constants.get("bands");
        assertEquals(0, bands.get(0).get("min").asInt());
        assertEquals(100, bands.get(bands.size() - 1).get("max").asInt());
        for (int i = 1; i < bands.size(); i++) {
            assertEquals(bands.get(i - 1).get("max").asInt() + 1, bands.get(i).get("min").asInt(),
                    "bands must cover 0-100 without gaps");
        }
    }

    @Test
    void internalResultShapeIsPublicShapePlusPOrganic() {
        Set<String> publicKeys = new TreeSet<>();
        Iterator<String> publicFields = read("analyze-response.schema.json").at("/$defs/result/properties").fieldNames();
        publicFields.forEachRemaining(publicKeys::add);

        Set<String> internalKeys = new TreeSet<>();
        Iterator<String> internalFields = read("score-response.schema.json").at("/$defs/result/properties").fieldNames();
        internalFields.forEachRemaining(internalKeys::add);

        internalKeys.remove("pOrganic");
        assertEquals(publicKeys, internalKeys,
                "the internal result may only add pOrganic to the public result shape");
    }
}
