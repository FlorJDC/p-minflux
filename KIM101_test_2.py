# -*- coding: utf-8 -*-
"""

Created on August 10 18:48:19 2023

@author: 
"""
import os
import time
import sys
import clr

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.InertialMotorCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.KCube.InertialMotorCLI import *
from System import Decimal  # necessary for real world units

def main():
    """The main entry point for the application"""

    # Uncomment this line if you are using
    SimulationManager.Instance.InitializeSimulations()

    try:

        DeviceManagerCLI.BuildDeviceList()

        #Creating new device
        serial_no_device1 = "97102222"  # Replace this line with your device's serial number
        print("Serial number 1: ", serial_no_device1)
        
        #Adding a new device
        serial_no_device2 = "74000002"
        print("Serial number 2: ", serial_no_device2)
        
        device1 = KCubeInertialMotor.CreateKCubeInertialMotor(serial_no_device1)
        device2 = KCubeInertialMotor.CreateKCubeInertialMotor(serial_no_device2)
        
        # Connection to devices
        device1.Connect(serial_no_device1)
        print("Device 1 connected")
        device2.Connect(serial_no_device2)
        print("Device 2 connected")
        time.sleep(0.25)


        # To be sure that the device settings have been initialized
        if not device1.IsSettingsInitialized():
            device1.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert device1.IsSettingsInitialized() is True

        # Get Device Information and display description
        device1_info = device1.GetDeviceInfo()
        print(device1_info.Description)
        # Start polling and enable channel
        device1.StartPolling(250)  #250ms polling rate
        time.sleep(5)
        device1.EnableDevice()
        time.sleep(0.25)  # Wait for device to enable

        # Load any configuration settings needed by the controller/stage
        inertial_motor_config1 = device1.GetInertialMotorConfiguration(serial_no_device1)
        print("Type inertial motor config: ",type(inertial_motor_config1))
        # Get parameters related to homing/zeroing/moving
        device_settings1 = ThorlabsInertialMotorSettings.GetSettings(inertial_motor_config1)
        
        # Load any configuration settings needed by the controller/stage
        inertial_motor_config2 = device2.GetInertialMotorConfiguration(serial_no_device2)
        print("Type inertial motor config: ",type(inertial_motor_config2))
        # Get parameters related to homing/zeroing/moving
        device_settings2 = ThorlabsInertialMotorSettings.GetSettings(inertial_motor_config2)
        
        #Mirror 1
        # Step parameters for an intertial motor channel 1
        chan1 = InertialMotorStatus.MotorChannels.Channel1  # enum chan ident
        device_settings1.Drive.Channel(chan1).StepRate = 500
        device_settings1.Drive.Channel(chan1).StepAcceleration = 100000
        
        #Channel 2
        chan2 = InertialMotorStatus.MotorChannels.Channel2  # enum chan ident
        device_settings1.Drive.Channel(chan2).StepRate = 500
        device_settings1.Drive.Channel(chan2).StepAcceleration = 100000
        
        #Mirror2
        #Channel 3
        chan3 = InertialMotorStatus.MotorChannels.Channel3  # enum chan ident
        device_settings1.Drive.Channel(chan3).StepRate = 500
        device_settings1.Drive.Channel(chan3).StepAcceleration = 100000
        
        #Channel 4
        chan4 = InertialMotorStatus.MotorChannels.Channel3  # enum chan ident
        device_settings1.Drive.Channel(chan4).StepRate = 500
        device_settings1.Drive.Channel(chan4).StepAcceleration = 100000

        #Send settings to the device
        device1.SetSettings(device_settings1, True, True)

        # Home or Zero the device (if a motor/piezo)
        device1.SetPositionAs(chan1, 0)
        print("Zeroing device, chan1 done")
        device1.SetPositionAs(chan2, 0)
        print("Success in zeroing device, chan2 done")
        device1.SetPositionAs(chan3, 0)
        device1.SetPositionAs(chan4, 0)

        # Move the device to a new position
        '''
        There are two versions of each movement Method in the API,
        with the same names but different inputs. 
        
        Methods that take an integer argument as an input move in terms of 
        device steps (step size can be user-defined). These methods are 
        used in open-loop operation.
        
        Methods that take a Decimal argument as an input move in real units.
        These methods are used in open closed-loop operation.        
        '''
        #new_pos = Decimal(5.0)
        # uncomment the following for open-loop operation:
        new_pos = int(400)
        new_pos2=int(300)
        new_pos3=int(300)
        new_pos4=int(300)
        print(f'Moving to position {new_pos}')
        # Pythonnet will infer which method to use:
        device1.MoveTo(chan1, new_pos, 60000)
        device1.MoveTo(chan2, new_pos2, 60000)  # 60 second timeout
        device1.MoveTo(chan3, new_pos3, 60000)
        device1.MoveTo(chan4, new_pos4, 60000)
        print("Move Complete device 1")

        #Mirror 3
        # Step parameters for an intertial motor channel 1
        chan1 = InertialMotorStatus.MotorChannels.Channel1  # enum chan ident
        device_settings2.Drive.Channel(chan1).StepRate = 500
        device_settings2.Drive.Channel(chan1).StepAcceleration = 100000
        
        #Channel 2
        chan2 = InertialMotorStatus.MotorChannels.Channel2  # enum chan ident
        device_settings2.Drive.Channel(chan2).StepRate = 500
        device_settings2.Drive.Channel(chan2).StepAcceleration = 100000
        
        #Mirror4
        #Channel 3
        chan3 = InertialMotorStatus.MotorChannels.Channel3  # enum chan ident
        device_settings2.Drive.Channel(chan3).StepRate = 500
        device_settings2.Drive.Channel(chan3).StepAcceleration = 100000
        
        #Channel 4
        chan4 = InertialMotorStatus.MotorChannels.Channel3  # enum chan ident
        device_settings2.Drive.Channel(chan4).StepRate = 500
        device_settings2.Drive.Channel(chan4).StepAcceleration = 100000

        # Send settings to the device
        device2.SetSettings(device_settings1, True, True)

        # Home or Zero the device (if a motor/piezo)
        device2.SetPositionAs(chan1, 0)
        print("Zeroing device, chan1 done")
        device2.SetPositionAs(chan2, 0)
        print("Success in zeroing device, chan2 done")
        device2.SetPositionAs(chan3, 0)
        device2.SetPositionAs(chan4, 0)

        # Move the device to a new position
      
        #Open-loop operation:
        new_pos5 = int(400)
        new_pos6=int(200)
        new_pos7=int(200)
        new_pos8=int(100)
        print(f'Moving to position {new_pos}')
        # Pythonnet will infer which method to use:
        device2.MoveTo(chan1, new_pos5, 60000)
        device2.MoveTo(chan2, new_pos6, 60000)  # 60 second timeout
        device2.MoveTo(chan3, new_pos7, 60000)
        device2.MoveTo(chan4, new_pos8, 60000)
        print("Move Complete device 2")

        # Stop Polling and Disconnect
        device1.StopPolling()
        device1.Disconnect()
        
        device2.StopPolling()
        device2.Disconnect()

    except Exception as e:
        print(e)

    # Uncomment this line if you are using Simulations
    SimulationManager.Instance.UninitializeSimulations()
    ...


if __name__ == "__main__":
    main()