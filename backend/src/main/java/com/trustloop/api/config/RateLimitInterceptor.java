package com.trustloop.api.config;

import com.trustloop.api.admin.DevMetrics;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.model.ApiError;
import com.trustloop.api.services.ContractValues;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;
import java.time.Clock;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitInterceptor implements HandlerInterceptor {
    private static final long WINDOW_MILLIS = 60_000L;
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;
    private final ContractValues contractValues;
    private final Clock clock;
    private final int configuredLimit;
    private final ObjectProvider<DevMetrics> devMetrics;

    public RateLimitInterceptor(
            ObjectMapper objectMapper,
            ContractValues contractValues,
            @Value("${trustloop.api.rate-limit-per-minute:60}") int configuredLimit,
            ObjectProvider<DevMetrics> devMetrics) {
        this.objectMapper = objectMapper;
        this.contractValues = contractValues;
        this.clock = Clock.systemUTC();
        this.configuredLimit = Math.max(1, Math.min(configuredLimit, contractValues.rateLimitPerMinute()));
        this.devMetrics = devMetrics;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws IOException {
        if (!"POST".equalsIgnoreCase(request.getMethod())
                || !"/api/v1/analyze".equals(request.getRequestURI())) {
            return true;
        }
        long now = clock.millis();
        String client = request.getRemoteAddr() == null ? "local" : request.getRemoteAddr();
        Window window = windows.compute(client, (key, current) -> {
            if (current == null || now - current.startedAt() >= WINDOW_MILLIS) {
                return new Window(now, 1);
            }
            return new Window(current.startedAt(), current.count() + 1);
        });
        if (window.count() <= configuredLimit) {
            return true;
        }
        DevMetrics metrics = devMetrics.getIfAvailable();
        if (metrics != null) metrics.recordReasonCode("RATE_LIMITED");
        String requestId = (String) request.getAttribute(ApiBoundaryFilter.REQUEST_ID_ATTRIBUTE);
        response.setStatus(429);
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(response.getOutputStream(),
                new ApiError(requestId, new ApiError.Error("RATE_LIMITED", "Request rejected.")));
        return false;
    }

    private record Window(long startedAt, int count) {
    }
}
