package com.trustloop.api.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trustloop.api.admin.DevMetrics;
import com.trustloop.api.model.ApiError;
import com.trustloop.api.services.ContractValues;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.io.BufferedReader;
import java.net.URI;
import java.net.URISyntaxException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.charset.Charset;
import jakarta.servlet.ReadListener;
import jakarta.servlet.ServletInputStream;
import jakarta.servlet.http.HttpServletRequestWrapper;
import java.util.Arrays;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class ApiBoundaryFilter extends OncePerRequestFilter {
    public static final String REQUEST_ID_ATTRIBUTE = "trustloop.requestId";
    private static final Pattern REQUEST_ID_PATTERN = Pattern.compile("^[A-Za-z0-9-]{1,64}$");
    private static final Set<String> ALLOWED_METHODS = Set.of("GET", "POST");
    private static final Set<String> ALLOWED_HEADERS = Set.of("content-type", "x-request-id");
    private static final AtomicLong REQUEST_COUNTER = new AtomicLong();

    private final ObjectMapper objectMapper;
    private final ContractValues contractValues;
    private final Set<String> allowedOrigins;
    private final ObjectProvider<DevMetrics> devMetrics;

    public ApiBoundaryFilter(
            ObjectMapper objectMapper,
            ContractValues contractValues,
            @Value("${trustloop.allowed-origins:}") String allowedOrigins,
            ObjectProvider<DevMetrics> devMetrics) {
        this.objectMapper = objectMapper;
        this.contractValues = contractValues;
        this.allowedOrigins = Arrays.stream(allowedOrigins.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isEmpty())
                .collect(Collectors.toUnmodifiableSet());
        this.devMetrics = devMetrics;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/v1/");
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        String configuredHeader = contractValues.requestIdHeader();
        String incomingRequestId = request.getHeader(configuredHeader);
        boolean invalidRequestId = incomingRequestId != null && !REQUEST_ID_PATTERN.matcher(incomingRequestId).matches();
        String requestId = incomingRequestId != null && !invalidRequestId
                ? incomingRequestId
                : "req-" + Long.toUnsignedString(System.nanoTime(), 36)
                + "-" + Long.toUnsignedString(REQUEST_COUNTER.incrementAndGet(), 36);
        request.setAttribute(REQUEST_ID_ATTRIBUTE, requestId);
        response.setHeader(configuredHeader, requestId);

        if (invalidRequestId) {
            writeError(response, requestId, HttpServletResponse.SC_BAD_REQUEST,
                    "INVALID_REQUEST", "Request rejected.");
            return;
        }
        if (request.getContentLengthLong() > contractValues.maxRequestBytes()) {
            writeError(response, requestId, HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE,
                    "PAYLOAD_TOO_LARGE", "Request rejected.");
            return;
        }

        String origin = request.getHeader("Origin");
        if (origin != null) {
            boolean configuredCrossOrigin = allowedOrigins.contains(origin);
            if (!configuredCrossOrigin && !isSameOrigin(origin, request)) {
                writeError(response, requestId, HttpServletResponse.SC_FORBIDDEN,
                        "INVALID_REQUEST", "Request rejected.");
                return;
            }
            if (configuredCrossOrigin) {
                response.setHeader("Access-Control-Allow-Origin", origin);
                response.addHeader("Vary", "Origin");
            }
            if ("OPTIONS".equalsIgnoreCase(request.getMethod())
                    && request.getHeader("Access-Control-Request-Method") != null) {
                String requestedMethod = request.getHeader("Access-Control-Request-Method");
                if (!ALLOWED_METHODS.contains(requestedMethod.toUpperCase())) {
                    writeError(response, requestId, HttpServletResponse.SC_BAD_REQUEST,
                            "INVALID_REQUEST", "Request rejected.");
                    return;
                }
                String requestedHeaders = request.getHeader("Access-Control-Request-Headers");
                if (requestedHeaders != null && Arrays.stream(requestedHeaders.split(","))
                        .map(String::trim)
                        .map(String::toLowerCase)
                        .anyMatch(header -> !ALLOWED_HEADERS.contains(header))) {
                    writeError(response, requestId, HttpServletResponse.SC_BAD_REQUEST,
                            "INVALID_REQUEST", "Request rejected.");
                    return;
                }
                if (configuredCrossOrigin) {
                    response.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                    response.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Request-Id");
                    response.setHeader("Access-Control-Expose-Headers", "X-Request-Id");
                }
                response.setStatus(HttpServletResponse.SC_NO_CONTENT);
                return;
            }
            if (configuredCrossOrigin) response.setHeader("Access-Control-Expose-Headers", "X-Request-Id");
        }

        filterChain.doFilter(new SizeLimitedRequest(request, contractValues.maxRequestBytes()), response);
    }

    private static boolean isSameOrigin(String origin, HttpServletRequest request) {
        try {
            URI parsed = new URI(origin);
            if (parsed.getScheme() == null || parsed.getHost() == null
                    || parsed.getRawUserInfo() != null || parsed.getRawQuery() != null
                    || parsed.getRawFragment() != null
                    || (parsed.getRawPath() != null && !parsed.getRawPath().isEmpty())) return false;
            if (!parsed.getScheme().equalsIgnoreCase(request.getScheme())
                    || !parsed.getHost().equalsIgnoreCase(request.getServerName())) return false;
            int originPort = parsed.getPort() >= 0 ? parsed.getPort()
                    : "https".equalsIgnoreCase(parsed.getScheme()) ? 443 : 80;
            int requestPort = request.getServerPort() >= 0 ? request.getServerPort()
                    : "https".equalsIgnoreCase(request.getScheme()) ? 443 : 80;
            return originPort == requestPort;
        } catch (URISyntaxException exception) {
            return false;
        }
    }

    private void writeError(HttpServletResponse response, String requestId, int status, String code, String message)
            throws IOException {
        DevMetrics metrics = devMetrics.getIfAvailable();
        if (metrics != null) metrics.recordReasonCode(code);
        response.setStatus(status);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType("application/json");
        objectMapper.writeValue(response.getOutputStream(),
                new ApiError(requestId, new ApiError.Error(code, message)));
    }

    private static final class SizeLimitedRequest extends HttpServletRequestWrapper {
        private final long maxBytes;
        private ServletInputStream limitedStream;

        private SizeLimitedRequest(HttpServletRequest request, long maxBytes) {
            super(request);
            this.maxBytes = maxBytes;
        }

        @Override
        public ServletInputStream getInputStream() throws IOException {
            if (limitedStream == null) {
                limitedStream = new SizeLimitedInputStream(super.getInputStream(), maxBytes);
            }
            return limitedStream;
        }

        @Override
        public BufferedReader getReader() throws IOException {
            String encoding = getCharacterEncoding();
            Charset charset = encoding == null ? StandardCharsets.UTF_8 : Charset.forName(encoding);
            return new BufferedReader(new InputStreamReader(getInputStream(), charset));
        }
    }

    private static final class SizeLimitedInputStream extends ServletInputStream {
        private final ServletInputStream delegate;
        private final long maxBytes;
        private long bytesRead;

        private SizeLimitedInputStream(ServletInputStream delegate, long maxBytes) {
            this.delegate = delegate;
            this.maxBytes = maxBytes;
        }

        @Override
        public int read() throws IOException {
            int value = delegate.read();
            if (value >= 0 && ++bytesRead > maxBytes) {
                throw new RequestBodyTooLargeException();
            }
            return value;
        }

        @Override
        public int read(byte[] buffer, int offset, int length) throws IOException {
            if (length == 0) {
                return 0;
            }
            long remaining = maxBytes - bytesRead;
            int boundedLength = (int) Math.min(length, remaining + 1);
            int count = delegate.read(buffer, offset, boundedLength);
            if (count > 0) {
                bytesRead += count;
                if (bytesRead > maxBytes) {
                    throw new RequestBodyTooLargeException();
                }
            }
            return count;
        }

        @Override
        public boolean isFinished() {
            return delegate.isFinished();
        }

        @Override
        public boolean isReady() {
            return delegate.isReady();
        }

        @Override
        public void setReadListener(ReadListener readListener) {
            delegate.setReadListener(readListener);
        }
    }

    public static final class RequestBodyTooLargeException extends IOException {
        private RequestBodyTooLargeException() {
            super("request body exceeds the configured limit");
        }
    }
}
