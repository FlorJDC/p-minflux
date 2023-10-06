# -*- coding: utf-8 -*-
"""
Created on Fri Oct  6 13:47:41 2023

@author: Cibion
"""

from ids_peak import ids_peak
#from ids_peak_ipl import ids_peak_ipl
import numpy as np
import cv2




def main():
        # initialize library
    ids_peak.Library.Initialize()

    # create a device manager object
    device_manager = ids_peak.DeviceManager.Instance()
    print("Type Device: ", type(device_manager))
    try:
        # update the device manager
        device_manager.Update()

        # exit program if no device was found
        if device_manager.Devices().empty():
            print("No device was found. Exiting Program.")
            return -1
        #Open first available device
        device = device_manager.Devices()[0].OpenDevice(ids_peak.DeviceAccessType_Control)
        #Get the remote device node map
        nodemap_remote_device= device.RemoteDevice().NodeMaps()[0]
        
        #Print model name and user ID
        print("Opening camera model: "+ nodemap_remote_device.FindNode("DeviceModeName").Value())
        nodemap_remote_device.FindNode("ExposureTime").SetValue(218000)
    except Exception as e:
        print("Exception: "+str(e)+"")
    finally:
        ids_peak.Library.Close()
        
if __name__ == '__main__':
   main()        
        