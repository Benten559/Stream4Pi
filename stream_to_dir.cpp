#include <iostream>
#include <sstream>
#include <ctime>
#include <chrono>
#include <thread>
#include <opencv2/opencv.hpp>
#include <raspicam/raspicam_cv.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <filesystem>

using namespace std;
using namespace cv;

class PiCameraInterface {
public:
    PiCameraInterface(const string& output_dir, int width = 680, int height = 480, int framerate = 24)
        : output_dir(output_dir), width(width), height(height), framerate(framerate) {
        camera.set(CAP_PROP_FRAME_WIDTH, width);
        camera.set(CAP_PROP_FRAME_HEIGHT, height);
        camera.set(CAP_PROP_FPS, framerate);
        camera.setRotation(2);
        timestamped_dir = createTimestampedDirectory();
    }

    void start(int duration) {
        if (!camera.open()) {
            cerr << "Error opening the camera" << endl;
            return;
        }

        auto start_time = chrono::steady_clock::now();
        while (chrono::duration_cast<chrono::seconds>(chrono::steady_clock::now() - start_time).count() < duration) {
            camera.grab();
            camera.retrieve(frame);
            saveFrame(frame);
        }

        camera.release();
    }

private:
    raspicam::RaspiCam_Cv camera;
    Mat frame;
    string output_dir;
    string timestamped_dir;
    int width, height, framerate;

    string createTimestampedDirectory() {
        time_t now = time(0);
        tm *ltm = localtime(&now);
        stringstream dir_name;
        dir_name << output_dir << "/" << 1900 + ltm->tm_year
                 << setfill('0') << setw(2) << 1 + ltm->tm_mon
                 << setfill('0') << setw(2) << ltm->tm_mday
                 << "-"
                 << setfill('0') << setw(2) << ltm->tm_hour
                 << setfill('0') << setw(2) << ltm->tm_min
                 << setfill('0') << setw(2) << ltm->tm_sec;

        string dir = dir_name.str();
        std::filesystem::create_directories(dir);

        return dir;
    }

    void saveFrame(const Mat& frame) {
        time_t now = time(0);
        tm *ltm = localtime(&now);
        stringstream filename;
        filename << timestamped_dir << "/" << 1900 + ltm->tm_year
                 << setfill('0') << setw(2) << 1 + ltm->tm_mon
                 << setfill('0') << setw(2) << ltm->tm_mday
                 << "-"
                 << setfill('0') << setw(2) << ltm->tm_hour
                 << setfill('0') << setw(2) << ltm->tm_min
                 << setfill('0') << setw(2) << ltm->tm_sec
                 << "-"
                 << setfill('0') << setw(6) << chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now().time_since_epoch()).count() % 1000000
                 << ".jpg";

        imwrite(filename.str(), frame);
    }
};

int main(int argc, char** argv) {
    string output_dir = "./output";
    int capture_duration = 10;  //in seconds

    PiCameraInterface camera(output_dir);
    camera.start(capture_duration);

    return 0;
}
