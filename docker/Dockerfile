FROM debian:bookworm-slim AS driver
ARG RTLSDR_REF=aed0ea19f3a273370a13c9009b96313c75d54c7b
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates build-essential cmake pkg-config libusb-1.0-0-dev \
 && rm -rf /var/lib/apt/lists/*
RUN git init /src && cd /src \
 && git remote add origin https://github.com/rtlsdrblog/rtl-sdr-blog \
 && git fetch --depth 1 origin "$RTLSDR_REF" && git checkout FETCH_HEAD \
 && cmake -S /src -B /src/build -DINSTALL_UDEV_RULES=OFF -DDETACH_KERNEL_DRIVER=ON \
 && cmake --build /src/build -j2 \
 && DESTDIR=/stage cmake --install /src/build \
 && mkdir -p /stage/usr/share/licenses/rtl-sdr-blog \
 && cp /src/COPYING /stage/usr/share/licenses/rtl-sdr-blog/COPYING

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libusb-1.0-0 python3 python3-venv ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*
COPY --from=driver /stage/ /
RUN ldconfig
WORKDIR /app
COPY addon/requirements.txt addon/pyproject.toml ./
COPY addon/taggle_rx/ ./taggle_rx/
RUN python3 -m venv /opt/rx \
 && /opt/rx/bin/pip install --no-cache-dir .
ENV PATH="/opt/rx/bin:$PATH" OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1 TZ=UTC
VOLUME ["/data"]
STOPSIGNAL SIGTERM
ENTRYPOINT ["taggle-rx"]
CMD ["--config", "/config/options.json"]
