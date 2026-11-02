package com.trustloop.api.controllers;

import com.trustloop.api.config.ApiBoundaryFilter;
import com.trustloop.api.model.AnalyzeRequest;
import com.trustloop.api.model.AnalyzeResponse;
import com.trustloop.api.services.AnalyzeService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class AnalyzeController {
    private final AnalyzeService analyzeService;

    public AnalyzeController(AnalyzeService analyzeService) {
        this.analyzeService = analyzeService;
    }

    @PostMapping("/analyze")
    public AnalyzeResponse analyze(
            @Valid @RequestBody AnalyzeRequest request,
            @RequestAttribute(ApiBoundaryFilter.REQUEST_ID_ATTRIBUTE) String requestId) {
        return analyzeService.analyze(request, requestId);
    }
}
