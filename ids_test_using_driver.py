# -*- coding: utf-8 -*-
"""
Created on Tue Nov  7 11:47:18 2023

@author: Minflux
"""


import drivers.ids_cam as ids_cam

device = ids_cam.IDS_U3()
print("type: ", type(device))
device.work()

