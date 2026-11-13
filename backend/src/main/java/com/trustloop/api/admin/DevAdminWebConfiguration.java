package com.trustloop.api.admin;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@Profile("dev-admin")
public class DevAdminWebConfiguration implements WebMvcConfigurer {
    private final DevMetricsInterceptor metricsInterceptor;

    public DevAdminWebConfiguration(DevMetricsInterceptor metricsInterceptor) {
        this.metricsInterceptor = metricsInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(metricsInterceptor).addPathPatterns("/api/v1/analyze");
    }
}
