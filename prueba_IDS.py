# -*- coding: utf-8 -*-
"""
Created on Thu Oct  5 15:16:26 2023

@author: Minflux
"""


import numpy as np
import cv2
from ids_peak import ids_peak

VERSION = "1.0.1"


def main():
    print("open_camera Sample v" + VERSION)

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
            print("No device found. Exiting Program.")
            return
        
        # list all available devices
        # for i, device in enumerate(device_manager.Devices()):
        #     print(str(i) + ": " + device.ModelName() + " ("
        #           + device.ParentInterface().DisplayName() + "; "
        #           + device.ParentInterface().ParentSystem().DisplayName() + "v."
        #           + device.ParentInterface().ParentSystem().Version() + ")")

        # # select a device to open
        # selected_device = None
        # print("Nro de dispositivos: ", range(len(device_manager.Devices())))
        # while True:
        #     try:
        #         selected_device = int(input("Select device to open: "))
        #         if selected_device in range(len(device_manager.Devices())):
        #             break
        #         else:
        #             print("Invalid ID.")
        #     except ValueError:
        #         print("Please enter a correct id.")
        #         continue

        # open selected device
        device = device_manager.Devices()[1].OpenDevice(ids_peak.DeviceAccessType_Control)
        print("llego aqui")
        # get the remote device node map
        nodemap_remote_device = device.RemoteDevice().NodeMaps()[0]
        print("Llego aqui 2")

        # print model name and user ID
        print("Model Name: " + nodemap_remote_device.FindNode("DeviceModelName").Value())
        try:
            print("User ID: " + nodemap_remote_device.FindNode("DeviceUserID").Value())
        except ids_peak.Exception:
            print("User ID: (unknown)")

        # print sensor information, not knowing if device has the node "SensorName"
        try:
            print("Sensor Name: " + nodemap_remote_device.FindNode("SensorName").Value())
        except ids_peak.Exception:
            print("Sensor Name: " + "(unknown)")

        # print resolution
        try:
            print("Max. resolution (w x h): "
                  + str(nodemap_remote_device.FindNode("WidthMax").Value()) + " x "
                  + str(nodemap_remote_device.FindNode("HeightMax").Value()))
        except ids_peak.Exception:
            print("Max. resolution (w x h): (unknown)")

    except Exception as e:
        print("Exception: " + str(e) + "")

    finally:
        input("Press Enter to continue...")
        ids_peak.Library.Close()


if __name__ == '__main__':
    main()