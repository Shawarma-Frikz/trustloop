package com.trustloop.api.controllers;

import com.trustloop.api.config.ApiBoundaryFilter;
import com.trustloop.api.admin.DevMetrics;
import com.trustloop.api.model.AnalyzeRequest;
import com.trustloop.api.model.AnalyzeResponse;
import com.trustloop.api.services.AnalyzeService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class AnalyzeController {
    private final AnalyzeService analyzeService;
    private final ObjectProvider<DevMetrics> devMetrics;

    public AnalyzeController(AnalyzeService analyzeService, ObjectProvider<DevMetrics> devMetrics) {
        this.analyzeService = analyzeService;
        this.devMetrics = devMetrics;
    }

    @PostMapping("/analyze")
    public AnalyzeResponse analyze(
            @Valid @RequestBody AnalyzeRequest request,
            @RequestAttribute(ApiBoundaryFilter.REQUEST_ID_ATTRIBUTE) String requestId) {
        AnalyzeResponse response = analyzeService.analyze(request, requestId);
        DevMetrics metrics = devMetrics.getIfAvailable();
        if (metrics != null) metrics.recordResults(response.results());
        return response;
    }
}
