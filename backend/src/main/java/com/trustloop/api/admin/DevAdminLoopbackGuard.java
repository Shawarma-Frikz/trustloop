package com.trustloop.api.admin;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("dev-admin")
public class DevAdminLoopbackGuard {
    private final String serverAddress;
    private final boolean localOnly;

    public DevAdminLoopbackGuard(
            @Value("${server.address:}") String serverAddress,
            @Value("${app.admin.local-only:false}") boolean localOnly) {
        this.serverAddress = serverAddress;
        this.localOnly = localOnly;
    }

    @PostConstruct
    void requireLoopback() {
        boolean loopback = "127.0.0.1".equals(serverAddress) || "::1".equals(serverAddress);
        if (!localOnly || !loopback) {
            throw new IllegalStateException("The dev-admin profile requires app.admin.local-only=true and a loopback server.address; refusing to start.");
        }
    }
}
