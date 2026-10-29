# Backend

Spring Boot public API. Base package `com.trustloop.api`.

## Prerequisites

- JDK 21 or newer (the build targets Java 21)
- Maven 3.9+

## Run

```bat
cd backend
mvn spring-boot:run
```

The app binds to `127.0.0.1:8080`. No endpoint is implemented yet; the contract lands in step 0.2.

## Test

```bat
cd backend
mvn test
```

## Configuration

Read from the environment, never committed:

| Variable | Default |
|---|---|
| `TRUSTLOOP_SCORING_URL` | `http://127.0.0.1:8000` |
| `TRUSTLOOP_SCORING_TOKEN` | empty |

`server.address=127.0.0.1` keeps the API off the network by default.
