# \file    mainwindow.py
# \author  IDS Imaging Development Systems GmbH
# \date    2022-06-01
# \since   1.2.0
#
# \version 1.3.0
#
# Copyright (C) 2021 - 2023, IDS Imaging Development Systems GmbH.
#
# The information in this document is subject to change without notice
# and should not be construed as a commitment by IDS Imaging Development Systems GmbH.
# IDS Imaging Development Systems GmbH does not assume any responsibility for any errors
# that may appear in this document.
#
# This document, or source code, is provided solely as an example of how to utilize
# IDS Imaging Development Systems GmbH software libraries in a sample application.
# IDS Imaging Development Systems GmbH does not assume any responsibility
# for the use or reliability of any portion of this document.
#
# General permission to copy or modify is hereby granted.

import sys
from datetime import datetime

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5 import QtWidgets
#from PyQt5.QtWidgets import QMainWindow, QApplication, QFrame, QGraphicsLayoutWidget, QGraphicsView, QGraphicsView, QGraphicsView, QGridLayout
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMessageBox

from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak import ids_peak_ipl_extension

from display_pyqt5 import Display

VERSION = "1.2.0"
FPS_LIMIT = 30


class MainWindow(QtGui.QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Focus lock widget
         
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        #self.setMinimumSize(width, height)
        self.setMinimumSize(2,200)
        
        # camera display
        
        self.camDisplay = pg.GraphicsLayoutWidget()
        self.camDisplay.setMinimumHeight(300)
        self.camDisplay.setMinimumWidth(300)
        
        self.vb = self.camDisplay.addViewBox(row=0, col=0)
        self.vb.setAspectLocked(True)
        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        
        # GUI layout
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        

        self.__device = None
        self.__nodemap_remote_device = None
        self.__datastream = None
        
        #Variables de instancia relacionadas con laadquisición de imágenes
        self.__display = None
        self.__acquisition_timer = QtCore.QTimer() #temporizador para controlar la frecuencia de adquisición,
        self.__frame_counter = 0 #Contador del numero de cuadros
        self.__error_counter = 0 #Contador del numero de errores
        self.__acquisition_running = False #bandera para indicar si la adquisición está en curso.
        #Declara variables de instancia para etiquetas de información en la GUI, incluyendo la versión de la aplicación y un enlace "Acerca de Qt".
        self.__label_infos = None
        self.__label_version = None
        self.__label_aboutqt = None

        # initialize peak library
        ids_peak.Library.Initialize()

        if self.__open_device():
            try:
                # Create a display for the camera image
                self.__display = Display()
                grid.addWidget(self.__display, 0, 0)
                if not self.__start_acquisition():
                    print( "Unable to start acquisition!")
            except Exception as e:
                print("Exception", str(e))

        else:
            self.__destroy_all()
            sys.exit(0)

        #self.__create_statusbar()

        self.setMinimumSize(700, 500)
        
    def __del__(self):
        self.__destroy_all()

    def __destroy_all(self):
        # Stop acquisition
        self.__stop_acquisition()

        # Close device and peak library
        self.__close_device()
        ids_peak.Library.Close()

    def __open_device(self):
        try:
            # Create instance of the device manager
            device_manager = ids_peak.DeviceManager.Instance()

            # Update the device manager
            device_manager.Update()

            # Return if no device was found
            if device_manager.Devices().empty():
                print( "Error", "No device found!")
                return False

            # Open the first openable device in the managers device list
            for device in device_manager.Devices():
                if device.IsOpenable():
                    self.__device = device.OpenDevice(ids_peak.DeviceAccessType_Control)
                    break

            # Return if no device could be opened
            if self.__device is None:
                print("Error", "Device could not be opened!")
                return False

            # Open standard data stream
            datastreams = self.__device.DataStreams()
            if datastreams.empty():
                print("Error", "Device has no DataStream!")
                self.__device = None
                return False

            self.__datastream = datastreams[0].OpenDataStream()

            # Get nodemap of the remote device for all accesses to the genicam nodemap tree
            self.__nodemap_remote_device = self.__device.RemoteDevice().NodeMaps()[0]

            # To prepare for untriggered continuous image acquisition, load the default user set if available and
            # wait until execution is finished
            try:
                self.__nodemap_remote_device.FindNode("UserSetSelector").SetCurrentEntry("Default")
                self.__nodemap_remote_device.FindNode("UserSetLoad").Execute()
                self.__nodemap_remote_device.FindNode("UserSetLoad").WaitUntilDone()
            except ids_peak.Exception:
                # Userset is not available
                pass

            # Get the payload size for correct buffer allocation
            payload_size = self.__nodemap_remote_device.FindNode("PayloadSize").Value()

            # Get minimum number of buffers that must be announced
            buffer_count_max = self.__datastream.NumBuffersAnnouncedMinRequired()

            # Allocate and announce image buffers and queue them
            for i in range(buffer_count_max):
                buffer = self.__datastream.AllocAndAnnounceBuffer(payload_size)
                self.__datastream.QueueBuffer(buffer)

            return True
        except ids_peak.Exception as e:
            print( "Exception", str(e))

            return False

    def __close_device(self):
        """
        Stop acquisition if still running and close datastream and nodemap of the device
        """
        # Stop Acquisition in case it is still running
        self.__stop_acquisition()

        # If a datastream has been opened, try to revoke its image buffers
        if self.__datastream is not None:
            try:
                for buffer in self.__datastream.AnnouncedBuffers():
                    self.__datastream.RevokeBuffer(buffer)
            except Exception as e:
                print("Exception", str(e))

    def __start_acquisition(self):
        """
        Start Acquisition on camera and start the acquisition timer to receive and display images

        :return: True/False if acquisition start was successful
        """
        # Check that a device is opened and that the acquisition is NOT running. If not, return.
        if self.__device is None:
            return False
        if self.__acquisition_running is True:
            return True

        # Get the maximum framerate possible, limit it to the configured FPS_LIMIT. If the limit can't be reached, set
        # acquisition interval to the maximum possible framerate
        try:
            max_fps = self.__nodemap_remote_device.FindNode("AcquisitionFrameRate").Maximum()
            print("Max Frame Rate: ", max_fps, "FPS_LIMIT: ", FPS_LIMIT)
            target_fps = min(max_fps, FPS_LIMIT)
            self.__nodemap_remote_device.FindNode("AcquisitionFrameRate").SetValue(target_fps)
        except ids_peak.Exception:
            # AcquisitionFrameRate is not available. Unable to limit fps. Print warning and continue on.
            print( "Warning",
                                "Unable to limit fps, since the AcquisitionFrameRate Node is"
                                " not supported by the connected camera. Program will continue without limit.")

        # Setup acquisition timer accordingly
        self.__acquisition_timer.setInterval((1 / target_fps) * 1000)
        self.__acquisition_timer.setSingleShot(False)
        self.__acquisition_timer.timeout.connect(self.on_acquisition_timer)#Esta linea es importante

        try:
            # Lock critical features to prevent them from changing during acquisition
            self.__nodemap_remote_device.FindNode("TLParamsLocked").SetValue(1)

            # Start acquisition on camera
            self.__datastream.StartAcquisition()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").Execute()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").WaitUntilDone()
        except Exception as e:
            print("Exception: " + str(e))
            return False

        # Start acquisition timer
        self.__acquisition_timer.start()
        self.__acquisition_running = True

        return True

    def __stop_acquisition(self):
        """
        Stop acquisition timer and stop acquisition on camera
        :return:
        """
        # Check that a device is opened and that the acquisition is running. If not, return.
        if self.__device is None or self.__acquisition_running is False:
            return

        # Otherwise try to stop acquisition
        try:
            remote_nodemap = self.__device.RemoteDevice().NodeMaps()[0]
            remote_nodemap.FindNode("AcquisitionStop").Execute()

            # Stop and flush datastream
            self.__datastream.KillWait()
            self.__datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
            self.__datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

            self.__acquisition_running = False

            # Unlock parameters after acquisition stop
            if self.__nodemap_remote_device is not None:
                try:
                    self.__nodemap_remote_device.FindNode("TLParamsLocked").SetValue(0)
                except Exception as e:
                    print( "Exception", str(e))

        except Exception as e:
            print("Exception", str(e))


    def update_counters(self):
        """
        This function gets called when the frame and error counters have changed
        :return:
        """
        self.__label_infos.setText("Acquired: " + str(self.__frame_counter) + ", Errors: " + str(self.__error_counter))

    @pyqtSlot()
    def on_acquisition_timer(self):
        """
        This function gets called on every timeout of the acquisition timer
        """
        try:
            # Get buffer from device's datastream
            buffer = self.__datastream.WaitForFinishedBuffer(5000)

            # Create IDS peak IPL image for debayering and convert it to RGBa8 format
            ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
            converted_ipl_image = ipl_image.ConvertTo(ids_peak_ipl.PixelFormatName_BGRa8)

            # Queue buffer so that it can be used again
            self.__datastream.QueueBuffer(buffer)

            # Get raw image data from converted image and construct a QImage from it
            image_np_array = converted_ipl_image.get_numpy_1D()
            image = QtWidgets.QImage(image_np_array,
                           converted_ipl_image.Width(), converted_ipl_image.Height(),
                           QtWidgets.QImage.Format_RGB32)

            # Make an extra copy of the QImage to make sure that memory is copied and can't get overwritten later on
            image_cpy = image.copy()

            # Emit signal that the image is ready to be displayed
            self.get_image(image_cpy)
            self.__display.update()

            # Increase frame counter
            self.__frame_counter += 1
        except ids_peak.Exception as e:
            self.__error_counter += 1
            print("Exception: " + str(e))

        # Update counters
        self.update_counters()
    
    def get_image(self, img):
        print(" Inside get_image ")
        self.img.setImage(img, autoLevels=False)
          
            

if __name__ == "__main__":
    if not QtGui.QApplication.instance():
        app = QtGui.QApplication([])
    else:
        app = QtGui.QApplication.instance()
        
    print(datetime.now(), '[mainwindow] Mainwindow module running in stand-alone mode')
    
    gui = MainWindow() #Mainwindow es Frontend
    gui.setWindowTitle('Focus lock')
    gui.resize(1500, 500)
    
    gui.show()


    app.exec_()
