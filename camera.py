from time import sleep

from picamera2 import Picamera2

class Camera():
    def __init__(self):
        """Camera constructor

        Initializes the underlying Picamera2 library
        """
        self.camera = Picamera2()
        self.camera.start()
        sleep(2)
    def takePicture(self):
        """takePicture

        Takes a single picture and return the pixel matrix
        """
        pass
    def takeVideo(self):
        """takeVideo

        Takes a video and saves it on the filesystem
        """
        pass