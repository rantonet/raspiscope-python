from multiprocessing import Process
from analysis        import Analysis
from eventManager    import EventManager
from camera          import Camera
from cuvetteSensor   import CuvetteSensor
from lightSource     import LightSource

c  = Camera()
cs = CuvetteSensor()
l  = LightSource()
a  = Analysis()

e = EventManager(c,cs,a,l)

e.run()