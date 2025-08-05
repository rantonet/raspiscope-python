import asyncio
import numpy

from communicator import Communicator

class Analisys():
    """Analisys

    Class for spectrogram analisys
    """    
    async def __init__(self):
        """Analisys constructor

        Initializes class members
        """
        self.communicator = Communicator("client")
        self.image = numpy.ndarray()
        self.strip = numpy.array()
    async def getStrip(self,centerX=0,centerY=0,length=0) -> numpy.array:
        """getStrip

        Gets a strip of pixels from the pictures
        """
        strip = self.image[centerY,centerX-length/2:centerX+length/2,:]
        return strip
    async def getSpectrograph(self) -> numpy.array:
        """getSpectrograph

        Converts the led strip values to the values array
        """
        pass
    async def computeMaterials(self) -> str:
        """computeMaterials

        Finds the materials in the solution
        """
        pass
    async def compareSpectrographs(self) -> str:
        """compareSpectrographs

        Compares the spectrograph taken with those stored
        """
        pass
    #Signals
    class GettingStrip():
        """GettingStrip

        Signal for Getting Strip
        """
        pass
    class StripTaken():
        """StripTaken

        Signal for Strip Taken"
        """
        pass
    class GettingSpectrograph():
        """GettingSpectrograph

        Signal for Getting Spectrograph
        """
        pass
    class SpectrographTaken():
        """SpectrographTaken

        Signal for Spectrograph Taken
        """
        pass
    class ComputingMaterials():
        """ComputingMaterials

        Signal for Computing Materials
        """
        pass
    class MaterialsComputed():
        """MaterialsComputed

        Signal for Materials Computed
        """
        pass
    class ComparingSpectrographs():
        """ComparingSpectrographs

        Signal for Comparing Spectrographs
        """
        pass
    class SpectrographCompared():
        """SpectrographsCompared

        Signal for Spectrographs Compared
        """
        pass