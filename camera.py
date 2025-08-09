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
        #Casual samples
        N_SAMPLES = 100

        #Parameters intervals
        PARAM_RANGES = {
            "ExposureTime": (1000, 10000),
            "AnalogueGain": (1.0, 8.0),
            "Sharpness": (-1.0, 1.0),
            "Contrast": (-1.0, 1.0),
            "Saturation": (-1.0, 1.0)
        }

        #Balancing weights for sharpsness versus noise
        W_SHARP = 1.0
        W_NOISE = 0.5

        def measure_sharpness(img):
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            return cv2.Laplacian(gray, cv2.CV_64F).var()

        def estimate_noise(img):
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            noise = gray.astype(np.float32) - blur.astype(np.float32)
            return np.std(noise)

        def random_param():
            #Extract a dictionary of casual parameters
            return {
                name: np.random.uniform(low, high) if isinstance(low, float) or isinstance(high, float)
                    else int(np.random.randint(low, high + 1))
                for name, (low, high) in PARAM_RANGES.items()
            }

        with self.camera as picam2:
            #Base Configuration
            picam2.set_controls({"AeEnable": False, "AwbEnable": False})

            best_score = float("inf")
            best_params = None

            for i in range(N_SAMPLES):
                #Extract casual parameters
                params = random_param()

                #Apply controls
                picam2.set_controls(params)
                time.sleep(0.3)

                #Take picture and measure
                img = picam2.capture_array()
                sharp = measure_sharpness(img)
                noise = estimate_noise(img)

                #Compute the score (minimize)
                score = - (W_SHARP * sharp - W_NOISE * noise)

                if score < best_score:
                    best_score = score
                    best_params = params.copy()
                    print(f"[New best #{i+1}] score={score:.1f} | sharp={sharp:.1f}, noise={noise:.1f}")
                    print("           params:", {k: round(v, 2) for k, v in params.items()})

            #Apply the best configuration found
            print("\n🎯 Optimal parameters found:")
            for k, v in best_params.items():
                print(f"  {k}: {v:.2f}")
            picam2.set_controls(best_params)
            time.sleep(0.5)
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