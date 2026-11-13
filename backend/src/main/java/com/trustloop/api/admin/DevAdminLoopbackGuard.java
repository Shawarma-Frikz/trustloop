package com.trustloop.api.admin;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("dev-admin")
public class DevAdminLoopbackGuard {
    private final String serverAddress;

    public DevAdminLoopbackGuard(@Value("${server.address:}") String serverAddress) {
        this.serverAddress = serverAddress;
    }

    @PostConstruct
    void requireLoopback() {
        if (!"127.0.0.1".equals(serverAddress) && !"::1".equals(serverAddress)) {
            throw new IllegalStateException("The dev-admin profile must bind to 127.0.0.1; refusing to start.");
        }
    }
}
