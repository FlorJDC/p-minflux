# -*- coding: utf-8 -*-
"""
Created on Tue Dec  5 17:51:30 2023

@author: Florencia D. Choque
Trying to learn how to take live video with SDK2 for Andor Ixon
Adapted from the manual https://pylablib.readthedocs.io/en/stable/devices/Andor.html and from https://github.com/AlexShkarin/pyLabLib
"""


from pylablib.devices import Andor
import numpy as np  # import numpy for saving
#The cameras are identified by their index, starting from zero. To get the total number of cameras:
print(Andor.get_cameras_number_SDK2())
cam = Andor.AndorSDK2Camera(temperature=-50) #Here open() function is automatically called in que constructor init
print("Success opening cam")
# change some camera parameters
cam.set_exposure(50E-3)
print("Exposure time 50E-3")
cam.set_roi(0, 256, 0, 256, hbin=2, vbin=2)
print("ROI: 256px * 256px") 
# # start the stepping loop
images = []
for image in range(5):
    img = cam.snap()  # grab a single frame
    images.append(img)
    print(img.shape) #(128, 128) Why??
np.array(images).astype("<u2").tofile("frames.bmp")  # save frames as raw binary/tif/bmp ITried them but with no success

#It is important to close all camera connections before finishing your script. Otherwise, DLL resources might become permanently blocked, and the only way to solve it would be to restart the PC.
cam.close()
print("Success closing cam")