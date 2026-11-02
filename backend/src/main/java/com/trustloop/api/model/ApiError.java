package com.trustloop.api.model;

public record ApiError(String requestId, Error error) {
    public record Error(String code, String message) {
    }
}
