#!/usr/bin/env python3

import redis
import time
import os
import sys
from typing import Optional
from picamera2 import Picamera2
import cv2
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/cam_stream_client.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class RedisStreamer:
    def __init__(self, redis_host: str, redis_port: int, channel: str = 'camera_stream'):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.channel = channel
        self.redis_client: Optional[redis.Redis] = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass
            self.redis_client = None
            
    def connect(self):
        """Connect to Redis server"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            logging.info(f"Connected to Redis server {self.redis_host}:{self.redis_port}")
            
        except redis.ConnectionError as e:
            self.close()
            raise RuntimeError(f"Redis connection failed: {e}")
        except Exception as e:
            self.close()
            raise RuntimeError(f"Unexpected Redis error: {e}")
    
    def send_frame(self, frame):
        """Publish frame to Redis channel"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        # Encode frame as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
        
        if not result:
            raise RuntimeError("Failed to encode frame")
            
        # Convert to bytes
        frame_data = encoded_frame.tobytes()
        
        try:
            # Publish frame data to Redis channel
            subscribers = self.redis_client.publish(self.channel, frame_data)
            logging.debug(f"Published frame to {subscribers} subscribers")
            
        except redis.ConnectionError as e:
            raise RuntimeError(f"Failed to publish frame: {e}")


class PiCameraStreamer:
    def __init__(self, redis_host: str, redis_port: int, channel: str = 'camera_stream',
                 width: int = 680, height: int = 480, framerate: int = 24):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.channel = channel
        self.width = width
        self.height = height
        self.framerate = framerate
        self.frame_delay = 1.0 / framerate
        
        # Initialize camera
        self.camera = None
        self._camera_type = None
        self._setup_camera()
        
    def _setup_camera(self):
        """Setup camera - try Picamera2 first, fallback to OpenCV"""
        try:
            self.camera = Picamera2()
            self._camera_type = 'picam2'
            
            # Configure camera
            config = self.camera.create_preview_configuration(
                main={"size": (self.width, self.height)}
            )
            self.camera.configure(config)
            self.camera.start()
            
            logging.info("Using Picamera2")
            return
            
        except Exception as e:
            logging.warning(f"Picamera2 failed: {e}, trying OpenCV...")

        # Fallback to OpenCV
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise RuntimeError("Could not open camera")
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.framerate)
            self._camera_type = 'opencv'
            logging.info("Using OpenCV VideoCapture")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize any camera: {e}")
        
    def _capture_frame_picam2(self):
        """Capture frame using Picamera2"""
        try:
            frame = self.camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return cv2.rotate(frame, cv2.ROTATE_180)
        except Exception as e:
            raise RuntimeError(f"Picam2 capture failure: {e}")
            
    def _capture_frame_opencv(self):
        """Capture frame using OpenCV"""
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
        # Rotate 180 
        return cv2.rotate(frame, cv2.ROTATE_180)
        
    def capture_frame(self):
        """Capture a single frame"""
        if self._camera_type == "opencv":
            return self._capture_frame_opencv()
        elif self._camera_type == "picam2":
            return self._capture_frame_picam2()
        else:
            raise RuntimeError("No camera initialized")
            
    def start_camera(self):
        """Start the camera (already started in setup)"""
        pass
            
    def stop_camera(self):
        """Stop the camera"""
        if self._camera_type == "opencv" and self.camera:
            self.camera.release()
            logging.info("OpenCV camera released")
        elif self._camera_type == "picam2" and self.camera:
            self.camera.stop()
            logging.info("Picamera2 stopped")
            
    def reconnect_redis(self, max_attempts: int = 5):
        """Attempt to reconnect to Redis with retries"""
        for attempt in range(1, max_attempts + 1):
            try:
                streamer = RedisStreamer(self.redis_host, self.redis_port, self.channel)
                streamer.connect()
                logging.info("Successfully connected to Redis")
                return streamer
            except Exception as e:
                logging.error(f"Redis connection attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    logging.info("Waiting 2 seconds before retry...")
                    time.sleep(2)
                else:
                    raise
                    
    def start(self):
        """Start the camera streaming process"""
        try:
            self.start_camera()
            logging.info(f"Camera started with resolution {self.width}x{self.height} at {self.framerate} FPS")
            logging.info(f"Publishing to Redis channel: {self.channel}")
            
            frame_count = 0
            last_log_time = time.time()
            
            # Main streaming loop with reconnection
            while True:
                streamer = None
                try:
                    # Connect to Redis
                    streamer = self.reconnect_redis()
                    
                    # Continuous streaming
                    with streamer:
                        while True:
                            start_time = time.time()
                            
                            # Capture frame
                            frame = self.capture_frame()
                            
                            # Send frame to Redis
                            streamer.send_frame(frame)
                            frame_count += 1
                            
                            # Log stats every 30 seconds
                            current_time = time.time()
                            if current_time - last_log_time >= 30:
                                fps_actual = frame_count / (current_time - last_log_time)
                                logging.info(f"Published {frame_count} frames, actual FPS: {fps_actual:.1f}")
                                frame_count = 0
                                last_log_time = current_time
                            
                            # Control frame rate
                            elapsed = time.time() - start_time
                            sleep_time = max(0, self.frame_delay - elapsed)
                            if sleep_time > 0:
                                time.sleep(sleep_time)
                            
                except redis.ConnectionError as e:
                    logging.error(f"Redis connection lost: {e}")
                    logging.info("Attempting to reconnect in 5 seconds...")
                    time.sleep(5)
                except Exception as e:
                    logging.error(f"Streaming error: {e}")
                    logging.info("Attempting to reconnect in 5 seconds...")
                    time.sleep(5)
                finally:
                    if streamer:
                        streamer.close()
                        
        except KeyboardInterrupt:
            logging.info("Streaming stopped by user")
        finally:
            self.stop_camera()


def main():
    try:
        # Redis server details 
        redis_host = os.getenv('REDIS_HOST', '192.168.8.100')  # Your server IP
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        channel = os.getenv('CAMERA_CHANNEL', 'camera_stream')
        
        # Camera / Imagery configuration
        # width = int(os.getenv('FRAME_WIDTH', '680'))
        # height = int(os.getenv('FRAME_HEIGHT', '480'))
        width = int(os.getenv('FRAME_WIDTH', '480'))
        height = int(os.getenv('FRAME_HEIGHT', '320'))
        framerate = int(os.getenv('FRAME_RATE', '24'))
        
        logging.info(f"Starting camera streamer:")
        logging.info(f"  Redis server: {redis_host}:{redis_port}")
        logging.info(f"  Channel: {channel}")
        logging.info(f"  Resolution: {width}x{height}")
        logging.info(f"  Frame rate: {framerate} FPS")
        
        # Create and start streamer
        camera_streamer = PiCameraStreamer(
            redis_host=redis_host,
            redis_port=redis_port,
            channel=channel,
            width=width,
            height=height,
            framerate=framerate
        )
        camera_streamer.start()
        
    except Exception as e:
        logging.error(f"Fatal Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
