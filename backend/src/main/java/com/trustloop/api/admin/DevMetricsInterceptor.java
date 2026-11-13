package com.trustloop.api.admin;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Profile;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
@Profile("dev-admin")
public class DevMetricsInterceptor implements HandlerInterceptor {
    private static final String START_NANOS_ATTRIBUTE = DevMetricsInterceptor.class.getName() + ".startNanos";
    private final DevMetrics metrics;

    public DevMetricsInterceptor(DevMetrics metrics) {
        this.metrics = metrics;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        request.setAttribute(START_NANOS_ATTRIBUTE, System.nanoTime());
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception exception) {
        Object started = request.getAttribute(START_NANOS_ATTRIBUTE);
        if (started instanceof Long startNanos) metrics.record(System.nanoTime() - startNanos, response.getStatus());
    }
}
