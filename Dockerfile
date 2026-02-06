FROM debian:bookworm

# Add Raspberry Pi repository for picamera2
RUN apt update && apt install -y --no-install-recommends gnupg
RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
  && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 82B129927FA3303E
RUN apt update && apt -y upgrade

# Install Python and Picamera2
RUN apt update && apt install -y --no-install-recommends \
         python3-pip \
         python3-picamera2 \
     && apt-get clean \
     && apt-get autoremove \
     && rm -rf /var/cache/apt/archives/* \
     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install VENV requirements file
COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

COPY camera_streamer.py .

# Envs
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV CAMERA_ID=raspberrypi
ENV WIDTH=1920
ENV HEIGHT=1080
ENV JPEG_QUALITY=85
ENV L_WIDTH=1028
ENV L_HEIGHT=720
ENV FPS=30
ENV ROT=90

# Health check - verify Redis connection
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import redis; r = redis.Redis(host='${REDIS_HOST}', port=${REDIS_PORT}, decode_responses=False); r.ping()" || exit 1

# Run the camera streamer
CMD ["python3", "-u", "camera_streamer.py"]
