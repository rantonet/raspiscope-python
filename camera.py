import asyncio
import numpy

from picamera2 import Picamera2

from communicator import Communicator

class Camera():
    async def __init__(self):
        """Camera constructor

        Initializes the underlying Picamera2 library
        """
        self.communicator = Communicator("client")
        self.image = numpy.ndarray()
        self.camera = Picamera2()
        picam2.configure(picam2.create_still_configuration({"size": (1920,1080)}))
        self.camera.start()
    async def setCamera(self,settings=dict()):
        """setCamera

        Camera settings
        """
        self.camera.stop()
        picam2.configure(picam2.create_still_configuration({"size": (1920,1080)}))
        self.camera.start()
    async def calibrate(self):
        """calibrate

        Calibrate camera settings to improve image
        """
        pass
    async def takePicture(self) -> numpy.ndarray:
        """takePicture

        Takes a single picture and return the pixel matrix
        """
        self.image = picam2.capture_array()

        return self.image
    #Signals
    class CameraSet():
        """CameraSet

        Seignal for Camera Settings
        """
        async def __init__(self,data=dict()):
            self.data = data
    class CameraCalibrated():
        """CameraCalibrated

        Signal for Camera Calibrated
        """
        async def __init__(self,data=dict()):
            self.data = data
    class CalibratingCamera():
        """CalibratingCamera

        Signal for Calibrating Camera
        """
        async def __init__(self,data=dict()):
            self.data = data
    class TakingPicture():
        """TakingPicture

        Signal for Taking Picture
        """
        async def __init__(self,data=dict()):
            self.data = data
    class PictureTaken():
        """PictureTaken

        Signal for Picture Taken
        """
        async def __init__(self,data=dict()):
            self.data = data
    class NeedMoreLight():
        """NeedMoreLight

        Signal to ask for more light
        """
        async def __init__(self,data=dict()):
            self.data = data
    class NeedLessLight():
        """NeedLessLight

        Signal to ask for less light
        """
        async def __init__(self,data=dict()):
            self.data = data