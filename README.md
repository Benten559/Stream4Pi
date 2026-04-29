# Stream4Pi

Raspberry Pi camera streaming system using [picamera2](https://github.com/raspberrypi/picamera2) and Redis Streams.

The Pi captures frames at full sensor resolution (up to 12MP), publishes a low-res JPEG preview stream for live viewing, and writes a high-res YUV frame to a Redis hash for downstream processing.

## Architecture

```
Raspberry Pi
└── camera_streamer.py (producer)
      ├── camera_stream:<CAMERA_ID>  →  Redis Stream  (lores JPEG, for viewing)
      └── camera_hires:<CAMERA_ID>   →  Redis Hash    (full-res YUV, for processing)

Processor host
└── Processor_send.py
      ├── reads  camera_hires:<CAMERA_ID>
      └── writes camera_stream:processed  →  Redis Stream (processed JPEG)
```

## Running with Docker

```bash
docker build -t stream4pi .
docker run --privileged \
  -e REDIS_HOST=<host> \
  -e CAMERA_ID=raspberrypi \
  stream4pi
```

### Environment variables

| Variable       | Default        | Description                        |
|----------------|----------------|------------------------------------|
| `REDIS_HOST`   | `redis`        | Redis server hostname              |
| `REDIS_PORT`   | `6379`         | Redis server port                  |
| `CAMERA_ID`    | `raspberrypi`  | Key suffix for Redis entries       |
| `WIDTH`        | `1920`         | Main stream width (px)             |
| `HEIGHT`       | `1080`         | Main stream height (px)            |
| `L_WIDTH`      | `1028`         | Lores preview width (px)           |
| `L_HEIGHT`     | `720`          | Lores preview height (px)          |
| `FPS`          | `30`           | Target frame rate                  |
| `JPEG_QUALITY` | `85`           | JPEG quality for preview stream    |
| `ROT`          | `90`           | Sensor rotation (degrees)          |

## Utilities

- `stream_monitor.py` — connects to Redis and prints live FPS / frame size stats for both streams

## Legacy

The original C++ implementation (OpenCV + raspicam) lives in `cpp/`.
