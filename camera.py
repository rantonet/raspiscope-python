from time import sleep

from picamera2 import Picamera2

class Camera():
    async def __init__(self):
        """Camera constructor

        Initializes the underlying Picamera2 library
        """
        self.camera = Picamera2()
        self.camera.start()
        sleep(2)
    async def setCamera(self,settings=dict()):
        pass
    async def takePicture(self):
        """takePicture

        Takes a single picture and return the pixel matrix
        """
        pass
    async def takeVideo(self):
        """takeVideo

        Takes a video and saves it on the filesystem
        """
        pass