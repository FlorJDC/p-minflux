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
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSlot
import qdarkstyle

from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak import ids_peak_ipl_extension

from display import Display

VERSION = "1.2.0"
FPS_LIMIT = 30


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent = None):
        try:
            super().__init__(parent)
    
            self.widget = QtWidgets.QWidget(self)#widget principal (self.widget) 
            self.__layout = QtWidgets.QVBoxLayout()# un diseño vertical (self.__layout) para organizar los elementos de la GUI
            self.widget.setLayout(self.__layout) #configuración del widget principal como el widget central de la ventana principal.
            self.setCentralWidget(self.widget) 
    
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
            print("Success initializing constructor")
        except Exception as e:
            print("Error al inicializar MainWindow:", str(e))
            raise

        if self.__open_device():
            try:
                # Create a display for the camera image
                self.__display = Display()
                self.__layout.addWidget(self.__display)
                print("Succes calling Display module")
                if not self.__start_acquisition():
                    QtWidgets.QMessageBox.critical(self, "Unable to start acquisition!", QtWidgets.QMessageBox.Ok)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Exception", str(e), QtWidgets.QMessageBox.Ok)

        else:
            self.__destroy_all()
            sys.exit(0)

        self.__create_statusbar()

        self.setMinimumSize(700, 500)
        
    def __del__(self):
        self.__destroy_all()
        print("inside destroy_all")

    def __destroy_all(self):
        # Stop acquisition
        print("Inside destroy_all")
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
            print("Success in updating")

            # Return if no device was found
            if device_manager.Devices().empty():
                QtWidgets.QMessageBox.critical(self, "Error", "No device found!", QtWidgets.QMessageBox.Ok)
                return False

            # Open the first openable device in the managers device list
            for device in device_manager.Devices():
                if device.IsOpenable():
                    self.__device = device.OpenDevice(ids_peak.DeviceAccessType_Control)
                    break

            # Return if no device could be opened
            if self.__device is None:
                QtWidgets.QMessageBox.critical(self, "Error", "Device could not be opened!", QtWidgets.QMessageBox.Ok)
                return False

            # Open standard data stream
            datastreams = self.__device.DataStreams()
            if datastreams.empty():
                QtWidgets.QMessageBox.critical(self, "Error", "Device has no DataStream!", QtWidgets.QMessageBox.Ok)
                self.__device = None
                return False

            self.__datastream = datastreams[0].OpenDataStream()
            print("Success opening datastream")

            # Get nodemap of the remote device for all accesses to the genicam nodemap tree
            self.__nodemap_remote_device = self.__device.RemoteDevice().NodeMaps()[0]
            print("Success opening nodemap")

            # To prepare for untriggered continuous image acquisition, load the default user set if available and
            # wait until execution is finished
            try:
                print("line143")
                self.__nodemap_remote_device.FindNode("UserSetSelector").SetCurrentEntry("Default")
                print(1)
                self.__nodemap_remote_device.FindNode("UserSetLoad").Execute() #Esta es la linea del error
                print(2)
                self.__nodemap_remote_device.FindNode("UserSetLoad").WaitUntilDone()
                print("line147")
            except ids_peak.Exception:
                print("Userset is not available")
                pass

            # Get the payload size for correct buffer allocation
            payload_size = self.__nodemap_remote_device.FindNode("PayloadSize").Value()

            # Get minimum number of buffers that must be announced
            buffer_count_max = self.__datastream.NumBuffersAnnouncedMinRequired()

            # Allocate and announce image buffers and queue them
            for i in range(buffer_count_max):
                buffer = self.__datastream.AllocAndAnnounceBuffer(payload_size)
                self.__datastream.QueueBuffer(buffer)
            print("ready to say true")    
            return True
        except ids_peak.Exception as e:
            QtWidgets.QMessageBox.critical(self, "Exception", str(e), QtWidgets.QMessageBox.Ok)
        print("ready to say false")
        return False

    def __close_device(self):
        """
        Stop acquisition if still running and close datastream and nodemap of the device
        """
        # Stop Acquisition in case it is still running
        self.__stop_acquisition()
        print("inside close_device")

        # If a datastream has been opened, try to revoke its image buffers
        if self.__datastream is not None:
            try:
                for buffer in self.__datastream.AnnouncedBuffers():
                    self.__datastream.RevokeBuffer(buffer)
            except Exception as e:
                QtWidgets.QMessageBox.information(self, "Exception", str(e), QtWidgets.QMessageBox.Ok)

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
            QtWidgets.QMessageBox.warning(self, "Warning",
                                "Unable to limit fps, since the AcquisitionFrameRate Node is"
                                " not supported by the connected camera. Program will continue without limit.")

        # Setup acquisition timer accordingly
        self.__acquisition_timer.setInterval((1 / target_fps) * 1000)
        self.__acquisition_timer.setSingleShot(False)
        self.__acquisition_timer.timeout.connect(self.on_acquisition_timer)

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
                    QtWidgets.QMessageBox.information(self, "Exception", str(e), QtWidgets.QMessageBox.Ok)

        except Exception as e:
            QtWidgets.QMessageBox.information(self, "Exception", str(e), QtWidgets.QMessageBox.Ok)

    def __create_statusbar(self):
        status_bar = QtWidgets.QWidget(self.centralWidget())
        status_bar_layout = QtWidgets.QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.__label_infos = QtWidgets.QLabel(status_bar)
        self.__label_infos.setAlignment(Qt.AlignLeft)
        status_bar_layout.addWidget(self.__label_infos)
        status_bar_layout.addStretch()

        self.__label_version = QtWidgets.QLabel(status_bar)
        self.__label_version.setText("simple_live_qtwidgets v" + VERSION)
        self.__label_version.setAlignment(Qt.AlignRight)
        status_bar_layout.addWidget(self.__label_version)

        self.__label_aboutqt = QtWidgets.QLabel(status_bar)
        self.__label_aboutqt.setObjectName("aboutQt")
        self.__label_aboutqt.setText("<a href='#aboutQt'>About Qt</a>")
        self.__label_aboutqt.setAlignment(Qt.AlignRight)
        self.__label_aboutqt.linkActivated.connect(self.on_aboutqt_link_activated)
        status_bar_layout.addWidget(self.__label_aboutqt)
        status_bar.setLayout(status_bar_layout)

        self.__layout.addWidget(status_bar)

    def update_counters(self):
        """
        This function gets called when the frame and error counters have changed
        :return:
        """
        self.__label_infos.setText("Acquired: " + str(self.__frame_counter) + ", Errors: " + str(self.__error_counter))

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
            self.__display.on_image_received(image_cpy)
            self.__display.update()

            # Increase frame counter
            self.__frame_counter += 1
        except ids_peak.Exception as e:
            self.__error_counter += 1
            print("Exception: " + str(e))

        # Update counters
        self.update_counters()


    def on_aboutqt_link_activated(self, link):
        if link == "#aboutQt":
            QtWidgets.QMessageBox.aboutQt(self, "About Qt")
            
if __name__ == '__main__':
    print("starting application")
    app = QtWidgets.QApplication([])
    print("application started")

    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    print(QtCore.QDateTime.currentDateTime(), 'running in stand-alone mode')

    main_window = MainWindow()

    main_window.show()
    app.exec_()