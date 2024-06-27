# Pi4CameraStream
This repo contains source for streaming using PiCamera and (TODO) other camera interfaces.
<br><br>
TODOs include:
* Support for different cameras
* Networking support for server/cloud processing of imagery

### Build
```
./build.sh
```

### Dependencies (Linux)
Its using C++20 (cause why not, some of this may be overkill)
```
sudo apt update
sudo apt install build-essential g++ cmake git pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libgtk2.0-dev libatlas-base-dev gfortran python3-dev

```
***Build and Install openCV from source***
```
cd <YOUR_DIR>
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git
cd opencv
mkdir build
cd build
```
* Toggle as you please here:
```
cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
      -D ENABLE_NEON=ON \
      -D ENABLE_VFPV3=ON \
      -D BUILD_TESTS=OFF \
      -D INSTALL_PYTHON_EXAMPLES=OFF \
      -D BUILD_EXAMPLES=OFF ..
```
* Raspberry Pi 4 has 4 of em
```
make -j4
sudo make install
```

***Build and Install raspicam from source:***
```cd <YOUR_DIR>
git clone https://github.com/cedricve/raspicam
cd raspicam
mkdir build
cd build
cmake ..
make
sudo make install
```
* Dont forget to update links
```
sudo ldconfig
```

***Troubleshoot linkage***
* links not being found
```
echo "/usr/local/lib" | sudo tee /etc/ld.so.conf.d/raspicam.conf
```
* helpful line (just in case)
```
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
``` 