package com.trustloop.api.model;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.List;

public record AnalyzeRequest(
        @NotNull
        @Pattern(regexp = "^[a-z0-9]+(\\.[a-z0-9]+)*$")
        String adapterId,
        @Pattern(regexp = "^(en|fr)$")
        String languageHint,
        @NotEmpty
        @Size(max = 10)
        List<@NotNull @Valid AnalyzeReview> reviews) {

    public record AnalyzeReview(
            @NotNull
            @Size(min = 1, max = 64)
            @Pattern(regexp = "^[A-Za-z0-9_-]+$")
            String reviewKey,
            @NotNull
            @Size(min = 1, max = 2000)
            String text) {
    }
}
