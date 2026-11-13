package com.trustloop.api.controllers;

import com.trustloop.api.config.ApiBoundaryFilter;
import com.trustloop.api.admin.DevMetrics;
import com.trustloop.api.config.ApiBoundaryFilter.RequestBodyTooLargeException;
import com.trustloop.api.model.ApiError;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(ApiExceptionHandler.class);
    private final ObjectProvider<DevMetrics> devMetrics;

    public ApiExceptionHandler(ObjectProvider<DevMetrics> devMetrics) {
        this.devMetrics = devMetrics;
    }

    @ExceptionHandler({
            MethodArgumentNotValidException.class,
            BindException.class,
            HandlerMethodValidationException.class,
            MissingServletRequestParameterException.class,
            HttpRequestMethodNotSupportedException.class
    })
    public ResponseEntity<ApiError> invalidRequest(Exception exception, HttpServletRequest request) {
        return error(request, HttpStatus.BAD_REQUEST, "INVALID_REQUEST");
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiError> unreadableRequest(HttpMessageNotReadableException exception, HttpServletRequest request) {
        Throwable cause = exception;
        while (cause != null) {
            if (cause instanceof RequestBodyTooLargeException) {
                return error(request, HttpStatus.PAYLOAD_TOO_LARGE, "PAYLOAD_TOO_LARGE");
            }
            cause = cause.getCause();
        }
        return error(request, HttpStatus.BAD_REQUEST, "INVALID_REQUEST");
    }

    @ExceptionHandler(RequestBodyTooLargeException.class)
    public ResponseEntity<ApiError> oversizedStream(RequestBodyTooLargeException exception, HttpServletRequest request) {
        return error(request, HttpStatus.PAYLOAD_TOO_LARGE, "PAYLOAD_TOO_LARGE");
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiError> notFound(NoResourceFoundException exception, HttpServletRequest request) {
        return error(request, HttpStatus.NOT_FOUND, "INVALID_REQUEST");
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<ApiError> statusException(ResponseStatusException exception, HttpServletRequest request) {
        HttpStatus status = HttpStatus.valueOf(exception.getStatusCode().value());
        String code = status == HttpStatus.NOT_FOUND ? "INVALID_REQUEST" : "INTERNAL_ERROR";
        return error(request, status, code);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> internalError(Exception exception, HttpServletRequest request) {
        String requestId = requestId(request);
        LOGGER.error("request failed requestId={} exceptionType={}", requestId, exception.getClass().getSimpleName());
        return error(request, HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR");
    }

    private ResponseEntity<ApiError> error(HttpServletRequest request, HttpStatus status, String code) {
        DevMetrics metrics = devMetrics.getIfAvailable();
        if (metrics != null) metrics.recordReasonCode(code);
        return ResponseEntity.status(status)
                .body(new ApiError(requestId(request), new ApiError.Error(code, "Request rejected.")));
    }

    private String requestId(HttpServletRequest request) {
        Object requestId = request.getAttribute(ApiBoundaryFilter.REQUEST_ID_ATTRIBUTE);
        return requestId instanceof String value ? value : "unavailable";
    }
}
