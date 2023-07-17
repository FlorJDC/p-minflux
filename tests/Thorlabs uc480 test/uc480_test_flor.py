# -*- coding: utf-8 -*-
"""
Created on Tue Nov 13 11:14:13 2018

@author: USUARIO
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from instrumental.drivers.cameras import uc480
from instrumental import Q_
from pyqtgraph.Qt import QtCore
import time

sys.path.append('C:\Program Files\Thorlabs\Scientific Imaging\ThorCam')

myCamera = uc480.UC480_Camera()

print('Model {}'.format(myCamera.model))
print('Serial number {}'.format(myCamera.serial))

#raw_image = myCamera.grab_image(exposure_time='50 ms')

myCamera.start_live_video('10 Hz')
print("live_video mode:ON")
#time.sleep(1)
#print("Timesleep finished")
myCamera._set_exposure(Q_('50 ms')) # ms # 50 ms Thorcam, 5ms IDS cam
ET = myCamera._get_exposure() #añadidas por FLOR E
print('ET='+str(ET)) #añadidas por FLOR E
print("linea 30")
view_timer = QtCore.QTimer()
cam_time= 200 # 200 ms per acquisition
view_timer.start(cam_time)
print("linea 687")

raw_image = myCamera.latest_frame()

r = raw_image[:, :, 0]
g = raw_image[:, :, 1]
b = raw_image[:, :, 2]

image = np.sum(raw_image, axis=2)

plt.imshow(image, interpolation='None', cmap='viridis')

myCamera.close()
print("Camera closed")
