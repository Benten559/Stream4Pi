#!/usr/bin/env python3

import socket
import struct
import time
import os
import sys
from typing import Optional
from picamera2 import Picamera2
import cv2

class SocketStreamer:
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sockfd: Optional[socket.socket] = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        if self.sockfd:
            self.sockfd.close()
            self.sockfd = None
            
    def connect(self):
        # Create socket
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # Connect to server
            self.sockfd.connect((self.server_ip, self.server_port))
            print(f"Connected to server {self.server_ip}:{self.server_port}")
        except Exception as e:
            self.close()
            raise RuntimeError(f"Connection failed: {e}")
    
    def send_frame(self, frame):
        if not self.sockfd:
            raise RuntimeError("Socket not connected")
            
        # Encode frame as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
        
        if not result:
            raise RuntimeError("Failed to encode frame")
            
        # Convert to bytes
        frame_data = encoded_frame.tobytes()
        frame_size = len(frame_data)
        
        try:
            # Send frame size first (4 bytes, network byte order)
            size_data = struct.pack('!I', frame_size)
            self.sockfd.sendall(size_data)
            
            # Send frame data
            self.sockfd.sendall(frame_data)
            
        except socket.error as e:
            raise RuntimeError(f"Failed to send frame: {e}")


class PiCameraStreamer:
    def __init__(self, server_ip: str, server_port: int, 
                 width: int = 680, height: int = 480, framerate: int = 24):
        self.server_ip = server_ip
        self.server_port = server_port
        self.width = width
        self.height = height
        self.framerate = framerate
        self.frame_delay = 1.0 / framerate
        
        # Initialize camera
        self.camera = None
        self._setup_camera()
        
    def _setup_camera(self):
        """Setup camera"""
        try:
            self.camera = Picamera2()
            self._camera_type = 'picam2'
            self.camera.start()
            return
        except Exception as exp:
            raise RuntimeError("Dun broke") from exp

        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise RuntimeError("Could not open camera")
            
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, self.framerate)
        self._camera_type = 'opencv'
        print("Using OpenCV VideoCapture")
        
    def _capture_frame_picam2(self):
        frame = self.camera.capture_array()
        #if not frame:
         #   raise RuntimeError("Picam2 capture failure")
        return cv2.rotate(frame, cv2.ROTATE_180)
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
        return self._capture_frame_picam2()
            
    def start_camera(self):
        """Start the camera"""
        pass
            
    def stop_camera(self):
        """Stop the camera"""
        if self._camera_type == "opencv":
            self.camera.release() # recommned from opencv docs
        else:
            self.camera.stop()
            
    def reconnect(self, max_attempts: int = 5):
        """Attempt to reconnect to server with retries"""
        for attempt in range(1, max_attempts + 1):
            try:
                streamer = SocketStreamer(self.server_ip, self.server_port)
                streamer.connect()
                print("Successfully connected to server")
                return streamer
            except Exception as e:
                print(f"Connection attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    print("Waiting 2 seconds before retry...")
                    time.sleep(2)
                else:
                    raise
                    
    def start(self):
        """Start the camera streaming process"""
        try:
            self.start_camera()
            print(f"Camera started with resolution {self.width}x{self.height} at {self.framerate} FPS")
            
            # Main streaming loop with reconnection
            while True:
                streamer = None
                try:
                    # Connect to server
                    streamer = self.reconnect()
                    
                    # Continuous streaming
                    with streamer:
                        while True:
                            # Capture frame
                            frame = self.capture_frame()
                            
                            # Send frame
                            streamer.send_frame(frame)
                            
                            # Control frame rate
                            time.sleep(self.frame_delay)
                            
                except Exception as e:
                    print(f"Streaming error: {e}")
                    print("Attempting to reconnect in 5 seconds...")
                    time.sleep(5)
                finally:
                    if streamer:
                        streamer.close()
                        
        except KeyboardInterrupt:
            print("Streaming stopped by user")
        finally:
            self.stop_camera()


def main():
    try:
        # Get server details from environment variables
        server_ip = "192.168.8.100"#""#os.getenv('SERVER_IP')
        server_port_str = os.getenv('SERVER_PORT', "5555")
        
        if not server_ip or not server_port_str:
            raise RuntimeError("SERVER_IP and SERVER_PORT environment variables must be set")
            
        server_port = 5555#int(server_port_str)
        
        # Parse optional frame parameters with defaults
        width = int(os.getenv('FRAME_WIDTH', '680'))
        height = int(os.getenv('FRAME_HEIGHT', '480'))
        framerate = int(os.getenv('FRAME_RATE', '24'))
        
        print(f"Starting camera streamer:")
        print(f"  Server: {server_ip}:{server_port}")
        print(f"  Resolution: {width}x{height}")
        print(f"  Frame rate: {framerate} FPS")
        
        # Create and start streamer
        camera_streamer = PiCameraStreamer(server_ip, server_port, width, height, framerate)
        camera_streamer.start()
        
    except Exception as e:
        print(f"Fatal Error: {e}", file=sys.stderr)
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
