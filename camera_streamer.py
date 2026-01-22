#!/usr/bin/env python3
"""
High-Performance Camera Producer for Redis Streams
Uses Picamera2 hardware JPEG encoding for maximum FPS
"""

import time
import io
import logging
import redis
from picamera2 import Picamera2
from libcamera import Transform

#############################################################
# CONFIGURATION OPTIONS                                     #
#############################################################
# Target redis server using HOST:PORT                       #
# STREAM_NAME is the key on server for stream types         #
# Image config settings can support up to 4056 x 1080       #
# but only at 7-10 FPS, ~30 FPS with most smaller sizes     #
#############################################################
# Redis Stream settings
MAX_STREAM_LEN = 1  # Trim to last N entries
APPROX_TRIM = False # Use approximate trimming for speed
STREAM_NAME = "camera_stream:raspberrypi"
# Redis network settings
REDIS_HOST = "redis"
REDIS_PORT = 6379
# Raspberrypi Camera settings
WIDTH = 1920
HEIGHT = 1080
JPEG_QUALITY = 85
############################################################
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class RedisCameraProducer:
    """
    Sets up camera configuration and network send capabilities
    """
    def __init__(self):
        # init Redis connection
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False  # Keep binary data
        )
        
        # Try connection
        try:
            self.redis_client.ping()
            logging.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            logging.error(f"Redis connection failed: {e}")
            raise
        
        # Initialize camera
        self.picam2 = Picamera2()
        
        # Video config, sensor is mounted upside down to housing
        config = self.picam2.create_video_configuration(
            main={"size": (WIDTH, HEIGHT), "format": "YUV420"},
            transform=Transform(hflip=True, vflip=True)
        )
        
        self.picam2.configure(config)
        logging.info(f"Camera configured: {WIDTH}x{HEIGHT}, flipped 180")
        
        # Performance tracking
        self.frame_count = 0
        self.last_log = time.time()
        self.running = False
    
    def start(self):
        """Start camera and streaming loop"""
        self.picam2.start()
        logging.info(f"Camera started, streaming to: {STREAM_NAME}")
        self.running = True
        
        try:
            self._streaming_loop()
        except KeyboardInterrupt:
            logging.info("Shutting down...")
        finally:
            self.stop()
    
    def _streaming_loop(self):
        """Main capture and publish loop"""
        while self.running:
            try:
                buf = io.BytesIO()
                try:
                    self.picam2.capture_file(buf, format='jpeg', quality=JPEG_QUALITY)
                except TypeError:
                    self.picam2.capture_file(buf, format='jpeg')
                
                frame_bytes = buf.getvalue()
                
                # Push to Redis Stream
                self.redis_client.xadd(
                    STREAM_NAME,
                    {"image": frame_bytes},
                    maxlen=MAX_STREAM_LEN,
                    approximate=APPROX_TRIM
                )
                
                self.frame_count += 1
                self._log_performance(frame_bytes)
                
            except redis.RedisError as e:
                logging.error(f"Redis error: {e}")
                time.sleep(1)  # Back off on error
            except Exception as e:
                logging.error(f"Capture error: {e}")
                time.sleep(0.1)
    
    def _log_performance(self, frame_bytes):
        """Logs FPS and frame size every 2 seconds"""
        now = time.time()
        elapsed = now - self.last_log
        
        if elapsed >= 2.0:
            fps = self.frame_count / elapsed
            size_kb = len(frame_bytes) / 1024
            
            logging.info(
                f"{fps:.1f} FPS | {size_kb:.0f} KB/frame | "
                f"{fps * size_kb:.0f} KB/s"
            )
            
            self.frame_count = 0
            self.last_log = now
    
    def stop(self):
        """Cleanup camera and Redis"""
        self.running = False
        if hasattr(self, 'picam2'):
            self.picam2.stop()
            logging.info("Camera stopped")
        if hasattr(self, 'redis_client'):
            self.redis_client.close()
            logging.info("Redis connection closed")


if __name__ == "__main__":
    producer = RedisCameraProducer()
    producer.start()
