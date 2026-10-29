package com.trustloop.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "trustloop.scoring")
public record ScoringProperties(String url, String token) {
}
