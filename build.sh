#bin/bash

# g++ -o capture_pi_camera stream_to_dir.cpp -I/usr/local/include/opencv4 -I/usr/local/include/raspicam -L/usr/local/lib -lopencv_core -lopencv_imgcodecs -lopencv_highgui -lopencv_imgproc -lopencv_videoio -lraspicam_cv -lraspicam -lmmal -lmmal_core -lmmal_util -lvcos -lbcm_host
g++ -o capture_pi_camera stream_to_dir.cpp -O3 -I/usr/local/include/opencv4 -I/usr/local/include/raspicam -std=c++20 -L/usr/local/lib -lopencv_core -lopencv_imgcodecs -lopencv_highgui -lopencv_imgproc -lopencv_videoio -lraspicam_cv -lraspicam -lmmal -lmmal_core -lmmal_util -lvcos -lbcm_host