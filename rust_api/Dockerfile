FROM rust:1.78 AS builder

WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim

WORKDIR /app
RUN useradd --system --create-home --uid 10001 truckapp
COPY --from=builder /build/target/release/truckapp-rust-api /usr/local/bin/truckapp-rust-api

ENV TRUCKAPP_DATA_DIR=/app/data \
    RUST_API_BIND=0.0.0.0:8787

EXPOSE 8787
USER truckapp
ENTRYPOINT ["/usr/local/bin/truckapp-rust-api"]
