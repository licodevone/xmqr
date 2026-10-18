# syntax=docker/dockerfile:1
ARG RUST_VERSION=1.99.0

FROM rust:${RUST_VERSION}-slim-bookworm AS build
WORKDIR /src
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake perl pkg-config ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY scripts/collect_notices.py ./scripts/collect_notices.py
COPY packaging/notices ./packaging/notices
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 scripts/collect_notices.py --output /third-party-notices
RUN cargo build --locked --release --bins

FROM debian:bookworm-slim AS runtime-base
ARG VERSION=0.38.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/licodevone/xmqr" \
      org.opencontainers.image.licenses="MIT"
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgcc-s1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 xmqr \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin xmqr \
    && install -d -o 10001 -g 10001 -m 0750 /var/lib/xmqr
COPY --chown=10001:10001 LICENSE /usr/share/licenses/xmqr/LICENSE
COPY --chown=10001:10001 docs/third-party-licenses.md /usr/share/licenses/xmqr/third-party-licenses.md
COPY --from=build --chown=10001:10001 /third-party-notices /usr/share/licenses/xmqr/third-party
USER 10001:10001
STOPSIGNAL SIGTERM

FROM runtime-base AS admin
LABEL org.opencontainers.image.title="XMQR Admin"
COPY --from=build --chown=10001:10001 /src/target/release/mqtt-admin /usr/local/bin/mqtt-admin
RUN test "$(/usr/local/bin/mqtt-admin --version)" = "mqtt-admin ${VERSION}"
ENTRYPOINT ["/usr/local/bin/mqtt-admin"]

# Keep the broker as the final/default stage for existing docker build users.
FROM runtime-base AS runtime
LABEL org.opencontainers.image.title="XMQR Broker"
COPY --from=build --chown=10001:10001 /src/target/release/mqtt-broker /usr/local/bin/mqtt-broker
COPY --from=build --chown=10001:10001 /src/target/release/mqtt-admin /usr/local/bin/mqtt-admin
RUN test "$(/usr/local/bin/mqtt-broker --version)" = "mqtt-broker ${VERSION}" \
    && test "$(/usr/local/bin/mqtt-admin --version)" = "mqtt-admin ${VERSION}"
ENV MQTT_MODE=secure-mtls \
    MQTT_BIND=0.0.0.0:8883 \
    MQTT_STATE_DIR=/var/lib/xmqr
VOLUME ["/var/lib/xmqr"]
EXPOSE 8883
ENTRYPOINT ["/usr/local/bin/mqtt-broker"]
