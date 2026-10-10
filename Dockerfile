# syntax=docker/dockerfile:1
ARG RUST_VERSION=1.99.0

FROM rust:${RUST_VERSION}-slim-bookworm AS build
WORKDIR /src
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake perl pkg-config ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --locked --release --bins

FROM debian:bookworm-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgcc-s1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 xmqr \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin xmqr \
    && install -d -o 10001 -g 10001 -m 0750 /var/lib/xmqr
COPY --from=build --chown=10001:10001 /src/target/release/mqtt-broker /usr/local/bin/mqtt-broker
COPY --from=build --chown=10001:10001 /src/target/release/mqtt-admin /usr/local/bin/mqtt-admin
COPY --chown=10001:10001 LICENSE /usr/share/licenses/xmqr/LICENSE
COPY --chown=10001:10001 docs/third-party-licenses.md /usr/share/licenses/xmqr/third-party-licenses.md
ENV MQTT_MODE=secure-mtls \
    MQTT_BIND=0.0.0.0:8883 \
    MQTT_STATE_DIR=/var/lib/xmqr
VOLUME ["/var/lib/xmqr"]
EXPOSE 8883
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/mqtt-broker"]
