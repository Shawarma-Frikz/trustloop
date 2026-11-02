package com.trustloop.api;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import com.trustloop.api.config.ScoringProperties;

@SpringBootTest
class TrustLoopApiApplicationTests {

    @Autowired
    private ScoringProperties scoringProperties;

    @Test
    void contextLoads() {
    }

    @Test
    void expectedModelVersionIsPinnedForTheScoringBoundary() {
        org.junit.jupiter.api.Assertions.assertEquals("tl-text-1.1.0", scoringProperties.expectedModelVersion());
    }
}
