package com.trustloop.api.services;

import com.trustloop.api.config.ScoringProperties;
import com.trustloop.api.model.AnalyzeRequest;
import com.trustloop.api.model.AnalyzeResponse;
import com.trustloop.api.model.ScoreRequest;
import com.trustloop.api.model.ScoreResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

@Service
public class AnalyzeService {
    private static final Logger LOGGER = LoggerFactory.getLogger(AnalyzeService.class);
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");
    private static final Set<String> STATUSES = Set.of("SCORED", "SIGNALS_ONLY", "UNKNOWN");
    private static final Set<String> ENGINES = Set.of("MODEL", "SIGNALS_ONLY");
    private static final Set<String> REASONS = Set.of(
            "INSUFFICIENT_TEXT", "UNSUPPORTED_LANGUAGE", "SCORING_TIMEOUT", "SCORING_UNAVAILABLE");
    private static final Set<String> EVIDENCE = Set.of("LOW", "ADEQUATE");
    private static final Set<String> VERDICTS = Set.of(
            "STRONG_MANIPULATION_SIGNALS", "LIKELY_MANIPULATED", "INCONCLUSIVE",
            "MIXED_SIGNALS", "LIKELY_ORGANIC", "STRONG_ORGANIC_SIGNALS");
    private static final Set<String> SIGNAL_KINDS = Set.of(
            "REPEATED_PHRASING", "CROSS_REVIEW_DUPLICATE", "GENERIC_WORDING",
            "PROMOTIONAL_TONE", "EXTREME_CLAIMS", "CONCRETE_DETAIL", "LEXICAL_VARIETY");
    private static final Pattern MODEL_VERSION = Pattern.compile("^tl-text-\\d+\\.\\d+\\.\\d+$");

    private final ScoringClient scoringClient;
    private final ScoringProperties properties;
    private final ContractValues contractValues;

    public AnalyzeService(ScoringClient scoringClient, ScoringProperties properties, ContractValues contractValues) {
        this.scoringClient = scoringClient;
        this.properties = properties;
        this.contractValues = contractValues;
    }

    public AnalyzeResponse analyze(AnalyzeRequest request, String requestId) {
        ScoreRequest scoringRequest = toScoringRequest(request);
        try {
            ScoreResponse scoreResponse = scoringClient.score(scoringRequest, requestId);
            if (!isConsistent(request, scoreResponse)) {
                LOGGER.warn("scoring response rejected requestId={} reason=inconsistent_contract", requestId);
                return unavailable(request, requestId);
            }
            List<AnalyzeResponse.AnalyzeResult> results = scoreResponse.results().stream()
                    .map(this::toPublicResult)
                    .toList();
            return new AnalyzeResponse(requestId, results);
        } catch (ResourceAccessException exception) {
            LOGGER.warn("scoring call failed requestId={} failureType={}", requestId, exception.getClass().getSimpleName());
            return unavailable(request, requestId, "SCORING_TIMEOUT");
        } catch (RuntimeException exception) {
            LOGGER.warn("scoring call failed requestId={} failureType={}", requestId, exception.getClass().getSimpleName());
            return unavailable(request, requestId);
        }
    }

    private ScoreRequest toScoringRequest(AnalyzeRequest request) {
        Set<String> seen = new HashSet<>();
        List<ScoreRequest.Review> reviews = new ArrayList<>();
        for (AnalyzeRequest.AnalyzeReview review : request.reviews()) {
            String normalized = Normalizer.normalize(review.text(), Normalizer.Form.NFKC)
                    .strip()
                    .toLowerCase(Locale.ROOT);
            normalized = WHITESPACE.matcher(normalized).replaceAll(" ");
            boolean duplicate = !seen.add(normalized);
            reviews.add(new ScoreRequest.Review(review.reviewKey(), review.text(), duplicate));
        }
        return new ScoreRequest(reviews);
    }

    private boolean isConsistent(AnalyzeRequest request, ScoreResponse response) {
        if (response == null || response.results() == null || response.results().size() != request.reviews().size()) {
            return false;
        }
        for (int index = 0; index < request.reviews().size(); index++) {
            AnalyzeRequest.AnalyzeReview input = request.reviews().get(index);
            ScoreResponse.Result result = response.results().get(index);
            if (result == null || !input.reviewKey().equals(result.reviewKey())
                    || !STATUSES.contains(result.status()) || !ENGINES.contains(result.engine())
                    || result.signals() == null || result.signals().size() > 5) {
                return false;
            }
            if (result.signals().stream().anyMatch(signal -> signal == null
                    || !SIGNAL_KINDS.contains(signal.kind())
                    || signal.summary() == null || signal.summary().isBlank()
                    || signal.summary().length() > 200
                    || signal.contribution() != null
                    && (!Double.isFinite(signal.contribution()) || signal.contribution() < -1 || signal.contribution() > 1))) {
                return false;
            }
            if (!isStatusConsistent(result)) {
                return false;
            }
        }
        return true;
    }

    private boolean isStatusConsistent(ScoreResponse.Result result) {
        return switch (result.status()) {
            case "SCORED" -> result.engine().equals("MODEL")
                    && result.trustScore() != null && result.trustScore() >= 0 && result.trustScore() <= 100
                    && result.pOrganic() != null && Double.isFinite(result.pOrganic())
                    && result.pOrganic() >= 0 && result.pOrganic() <= 1
                    && result.trustScore() == (int) Math.floor(result.pOrganic() * 100 + 0.5)
                    && result.verdict() != null && VERDICTS.contains(result.verdict())
                    && result.verdict().equals(contractValues.verdictFor(result.trustScore()))
                    && result.evidenceQuality() != null && EVIDENCE.contains(result.evidenceQuality())
                    && result.reasonCode() == null
                    && properties.expectedModelVersion().equals(result.modelVersion());
            case "SIGNALS_ONLY" -> result.engine().equals("SIGNALS_ONLY")
                    && result.trustScore() == null && result.pOrganic() == null && result.verdict() == null
                    && result.modelVersion() == null && result.reasonCode() == null
                    && result.evidenceQuality() != null && EVIDENCE.contains(result.evidenceQuality())
                    && result.signals().stream().allMatch(signal -> signal.contribution() == null);
            case "UNKNOWN" -> result.reasonCode() != null && REASONS.contains(result.reasonCode())
                    && result.trustScore() == null && result.pOrganic() == null && result.verdict() == null
                    && (result.evidenceQuality() == null || EVIDENCE.contains(result.evidenceQuality()))
                    && (result.modelVersion() == null || MODEL_VERSION.matcher(result.modelVersion()).matches()
                    && properties.expectedModelVersion().equals(result.modelVersion()));
            default -> false;
        };
    }

    private AnalyzeResponse unavailable(AnalyzeRequest request, String requestId) {
        return unavailable(request, requestId, "SCORING_UNAVAILABLE");
    }

    private AnalyzeResponse unavailable(AnalyzeRequest request, String requestId, String reasonCode) {
        List<AnalyzeResponse.AnalyzeResult> results = request.reviews().stream()
                .map(review -> new AnalyzeResponse.AnalyzeResult(
                        review.reviewKey(), "UNKNOWN", null, null, null,
                        reasonCode, List.of(), properties.expectedModelVersion(), "MODEL"))
                .toList();
        return new AnalyzeResponse(requestId, results);
    }

    private AnalyzeResponse.AnalyzeResult toPublicResult(ScoreResponse.Result result) {
        List<AnalyzeResponse.Signal> signals = result.signals().stream()
                .map(signal -> new AnalyzeResponse.Signal(signal.kind(), signal.summary(), signal.contribution()))
                .toList();
        return new AnalyzeResponse.AnalyzeResult(
                result.reviewKey(), result.status(), result.trustScore(), result.verdict(),
                result.evidenceQuality(), result.reasonCode(), signals, result.modelVersion(), result.engine());
    }
}
