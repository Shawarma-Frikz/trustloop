package com.trustloop.api.services;

public class ScoringUnavailableException extends RuntimeException {
    public ScoringUnavailableException(String message) {
        super(message);
    }

    public ScoringUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
