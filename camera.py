import asyncio
import numpy

from picamera2 import Picamera2

from communicator import Communicator

class Camera():
    def __init__(self):
        """Camera constructor

        Initializes the underlying Picamera2 library
        """
        self.communicator = Communicator("client")
        self.image = numpy.ndarray()
        self.camera = Picamera2()
        picam2.configure(picam2.create_still_configuration({"size": (1920,1080)}))
        self.camera.start()
    async def run():
        await self.communicator.run()
        message = None
        while True:
            if self.communicator.incomingQueue:
                message = self.communicator.incomingQueue.pop(0)
            if message:
                if message["Message"] == "Stop":
                    break
                elif message["Message"] == "Set":
                    pass
                elif message["Message"] == "Calibrate":
                    pass
                elif message["Message"] == "Take":
                    pass
    async def setCamera(self,settings=dict()):
        """setCamera

        Camera settings
        """
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.SettingCamera()
                                    }
                                              )
        #Casual samples
        self.camera.stop()
        picam2.configure(picam2.create_still_configuration({"size": (1920,1080)}))
        self.camera.start()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.CameraSet()
                                    }
                                              )
        #Casual samples
        return True
    async def calibrate(self,
                        Samples           = 100,
                        ExposureTimeRange = (1000,10000),
                        AnalogueGainRange = (81.0,8.0),
                        SharpnessRange    = (-1.0,1.0),
                        ContrastRange     = (-1.0,1.0),
                        SaturationRange   = (-1.0,1.0),
                        SharpnessWeight   = 1.0,
                        NoiseWeight       = 0.5
                        ):
        """calibrate

        Calibrate camera settings to improve image
        """
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.CalibratingCamera()
                                    }
                                              )
        #Casual samples
        N_SAMPLES = Samples

        #Parameters intervals
        PARAM_RANGES = {
            "ExposureTime" : ExposureTimeRange,
            "AnalogueGain" : AnalogueGainRange,
            "Sharpness"    : SharpnessRange,
            "Contrast"     : ContrastRange,
            "Saturation"   : SaturationRange
        }

        #Balancing weights for sharpsness versus noise
        W_SHARP = SharpnessWeight
        W_NOISE = NoiseWeight

        with self.camera as picam2:
            #Base Configuration
            picam2.set_controls({"AeEnable": False, "AwbEnable": False})

            best_score = float("inf")
            best_params = None

            for i in range(N_SAMPLES):
                #Extract casual parameters
                params = {
                            name: numpy.random.uniform(low, high) if isinstance(low, float) or isinstance(high, float)
                                else int(numpy.random.randint(low, high + 1))
                            for name, (low, high) in PARAM_RANGES.items()
                        }

                #Apply controls
                picam2.set_controls(params)
                time.sleep(0.3)

                #Take picture and measure
                img   = picam2.capture_array()
                sharp = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()
                gray  = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                blur  = cv2.GaussianBlur(gray, (5, 5), 0)
                noise = gray.astype(numpy.float32) - blur.astype(numpy.float32)
                noise = numpy.std(noise)

                #Compute the score (minimize)
                score = - (W_SHARP * sharp - W_NOISE * noise)

                if score < best_score:
                    best_score = score
                    best_params = params.copy()
            self.camera.set_controls(best_params)
            time.sleep(0.5)
            self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.CameraCalibrated()
                                    }
                                              )
        return True
    async def takePicture(self) -> numpy.ndarray:
        """takePicture

        Takes a single picture and return the pixel matrix
        """
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.TakingPicture()
                                    }
                                              )
        self.image = picam2.capture_array()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Camera",
                                        "Destination" : "All",
                                        "Message"     : self.PictureTaken(
                                                                      self.image
                                                                         )
                                    }
                                              )
        return True
    #Signals
    class SettingCamera():
        """SettingCamera

        Seignal for Camera Settings
        """
        async def __init__(self,data=dict()):
            self.data = data
    class CameraSet():
        """CameraSet

        Seignal for Camera Settings
        """
        async def __init__(self,data=dict()):
            self.data = data
    class CalibratingCamera():
        """CalibratingCamera

        Signal for Calibrating Camera
        """
        async def __init__(self,data=dict()):
            self.data = data
    class CameraCalibrated():
        """CameraCalibrated

        Signal for Camera Calibrated
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