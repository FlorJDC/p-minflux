# -*- coding: utf-8 -*-
"""
Created on Th Oct  31 2023
Test using class

@authors: Flor C
"""

import numpy as np
import time
import scipy.ndimage as ndi
import matplotlib.pyplot as plt
from datetime import date, datetime
import os

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
import qdarkstyle # see https://stackoverflow.com/questions/48256772/dark-theme-for-in-qt-widgets

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets

import sys
sys.path.append('C:\Program Files\Thorlabs\Scientific Imaging\ThorCam')
# install from https://instrumental-lib.readthedocs.io/en/stable/install.html
import tools.viewbox_tools as viewbox_tools
import tools.tools as tools
import tools.PSF as PSF
import tools.colormaps as cmaps
from scipy import optimize as opt

from instrumental.drivers.cameras import uc480
from instrumental import Q_

from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak import ids_peak_ipl_extension

ids_peak.Library.Initialize()

FPS_LIMIT = 30


DEBUG = True

class Frontend(QtGui.QFrame):
    
    if DEBUG:
        print("Inside Frontend")

    closeSignal = pyqtSignal()

    
    """
    Signals
        
    - closeSignal:
        To: [backend] stop
        
    """
    
    def __init__(self, *args, **kwargs):
        if DEBUG:
            print("Inside init in frontend")

        super().__init__(*args, **kwargs)
        
        self.cropped = False

        self.setup_gui()
        
    @pyqtSlot(bool)        
    def toggle_liveview(self, on):
        if DEBUG:
            print("Inside toggle_liveview")
        if on:
            self.liveviewButton.setChecked(True)
            print(datetime.now(), '[toggle liveview activated] live view started')
        else:
            self.liveviewButton.setChecked(False)
            self.img.setImage(np.zeros((1002,1002)), autoLevels=False)

            print(datetime.now(), '[toggle liveview] live view stopped ')
            
        
    @pyqtSlot(np.ndarray)
    def get_image(self, img):
        if DEBUG:
            print(" Inside get_image ")
        print("Type of image received in get image", type(img))
        self.img.setImage(img, autoLevels=False)
        print("Image sent to GUI. Type: ", type(self.img))
                        
    def make_connection(self, backend):
        if DEBUG:
            print("Inside make_connetion in frontend")
        backend.changedImage.connect(self.get_image)
        backend.liveviewSignal.connect(self.toggle_liveview)

    def setup_gui(self):
        if DEBUG:
            print("Inside setup_gui")
        
         # Focus lock widget
         
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        #self.setMinimumSize(width, height)
        self.setMinimumSize(2,200)
        
        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('Camera LIVEVIEW')
        self.liveviewButton.setCheckable(True)

        # Camera display
        
        self.camDisplay = pg.GraphicsLayoutWidget()
        self.camDisplay.setMinimumHeight(300)
        self.camDisplay.setMinimumWidth(300)
        
        self.vb = self.camDisplay.addViewBox(row=0, col=0)
        self.vb.setAspectLocked(True)
        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        
        self.vb.addItem(self.img)
        
        self.hist = pg.HistogramLUTItem(image=self.img)   # set up histogram for the liveview image
        lut = viewbox_tools.generatePgColormap(cmaps.inferno)
        self.hist.gradient.setColorMap(lut)
        self.hist.vb.setLimits(yMin=0, yMax=10000)

        for tick in self.hist.gradient.ticks:
            tick.hide()
            
        self.camDisplay.addItem(self.hist, row=0, col=1)

        # GUI layout
        
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        
        # parameters widget
        
        self.paramWidget = QtGui.QFrame()
        self.paramWidget.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        #Widget size (widgets with buttons)
        self.paramWidget.setFixedHeight(330)
        self.paramWidget.setFixedWidth(140)
        
        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        
        subgrid.addWidget(self.liveviewButton, 1, 0, 1, 2)

        grid.addWidget(self.paramWidget, 0, 0)

        grid.addWidget(self.camDisplay, 0, 1)
        
        #didnt want to work when being put at earlier point in this function
        self.liveviewButton.clicked.connect(lambda: self.toggle_liveview(self.liveviewButton.isChecked()))
        print("liveviewbutton & toogle liveview connected")

    def closeEvent(self, *args, **kwargs):
        if DEBUG:
            print("Inside closeEvent")
        
        self.closeSignal.emit()
        time.sleep(1)
        
#        camThread.exit()
        super().closeEvent(*args, **kwargs)
        app.quit()
        
        
class Backend(QtCore.QObject):
    if DEBUG:
        print("Inside Backend")
    
    changedImage = pyqtSignal(np.ndarray)
    liveviewSignal = pyqtSignal(bool)


    """
    Signals
    
    - changedImage:
        To: [frontend] get_image

    """

    def __init__(self, *args, **kwargs):
        if DEBUG:
            print("Inside init in backend")
        super().__init__(*args, **kwargs)

        
        self.__device = None
        self.__nodemap_remote_device = None
        self.__datastream = None
        
        #Variables de instancia relacionadas con laadquisición de imágenes
        self.__display = None
        #self.__acquisition_timer = QTimer() #temporizador para controlar la frecuencia de adquisición,
        self.counter = 0 #Contador del numero de cuadros
        self.__error_counter = 0 #Contador del numero de errores
        self.__acquisition_running = False #bandera para indicar si la adquisición está en curso.
        
        
        self.standAlone = False
        self.camON = False
        self.roi_area = np.zeros(4)
        
        today = str(date.today()).replace('-', '') # TO DO: change to get folder from microscope
        root = r'C:\\Data\\'
        folder = root + today
        
        filename = r'zdata.txt'
        self.filename = os.path.join(folder, filename)
        
        self.save_data_state = False
    
        self.npoints = 400
        
        # checks image size
        
        #rawimage = self.camera.latest_frame()
        #image = np.sum(rawimage, axis=2)
#        self.sensorSize = np.array(image.shape)        
        self.pxSize = 50 #original 10nm FC  # in nm, TODO: check correspondence with GUI
        

        self.focusSignal = 0
        
        # set focus update rate
        
        self.scansPerS = 10

        self.camTime = 1000 / self.scansPerS
        self.cameraTimer = QtCore.QTimer()
        
        self.reset()
      
        if self.__open_device():
            print("Success opening IDS")
        else:
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
                print( "Error", "Device could not be opened!")
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
            print( "Warning: Unable to limit fps, since the AcquisitionFrameRate Node is not supported by the connected camera. Program will continue without limit.")

        # Setup acquisition timer accordingly
        self.cameraTimer.setInterval((1 / target_fps) * 1000) #Same timer than in uc480
        self.cameraTimer.setSingleShot(False)
        self.cameraTimer.timeout.connect(self.on_acquisition_timer)#Esta linea es importante
        print("inside line 365")
        try:
            # Lock critical features to prevent them from changing during acquisition
            self.__nodemap_remote_device.FindNode("TLParamsLocked").SetValue(1)

            # Start acquisition on camera
            self.__datastream.StartAcquisition()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").Execute()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").WaitUntilDone()
            print("Success starting acquisition - line 374")
        except Exception as e:
            print("Exception: " + str(e))
            return False

        # Start acquisition timer
        self.cameraTimer.start()
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
                    print("Exception", str(e))

        except Exception as e:
            print("Exception", str(e))

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
            ##converted_ipl_image = ipl_image.ConvertTo(ids_peak_ipl.PixelFormatName_BGRa8)

            # Queue buffer so that it can be used again
            self.__datastream.QueueBuffer(buffer)

            # Get raw image data from converted image and construct a QImage from it
            #image_np_array = converted_ipl_image.get_numpy_1D()
            #Esta linea me da error si no la comente, problema con el Qtwidgets.QImage
            #image = QImage(image_np_array, converted_ipl_image.Width(), converted_ipl_image.Height(), QImage.Format_RGB32)

            # Make an extra copy of the QImage to make sure that memory is copied and can't get overwritten later on
            self.image_cpy = ipl_image #.copy()
            print(" image_cpy: ", self.image_cpy)

            # Emit signal that the image is ready to be displayed
            self.changedImage.emit(self.image_cpy)
            self.counter = self.counter + 1
            print("Image number: ", self.counter, " sent")
            #self.__display.on_image_received(image_cpy)
            #self.__display.update()

        except ids_peak.Exception as e:
            self.__error_counter += 1
            print("Exception: " + str(e))


    @pyqtSlot(bool)
    def liveview(self, value):
        if value:
            try:
                if self.__start_acquisition():
                    print("Acquisition started!")
                    self.on_acquisition_timer()
                    print("camera started live video mode")
                    self.cameraTimer.start() #self.camTime
                    print("timer started in liveview_start")
            except Exception as e:
                    print("Exception", str(e))
        else:
            try:
                self.__stop_acquisition()
                print("Acquisition stopped!")
                self.cameraTimer.stop()
                print("cameraTimer: stopped")
            except Exception as e:
                print("Exception", str(e))

    def update(self):
        if DEBUG:
                print("Inside update")
        
        self.acquire_data()
        
        if self.save_data_state:
            pass
            
    def acquire_data(self): #Es update_view en otros códigos
        if DEBUG:
                print("Inside acquire_data")
                
        # acquire image
    
        raw_image = self.camera.latest_frame()

        #self.image = np.sum(raw_image, axis=2)  #comment FC 28-9 # sum the R, G, B images
        self.image = raw_image[:, :, 0] #Comment FC para colocar IDS # take only R channel
        #self.image = raw_image #Esta linea es para ids, comentar para thorcam
        # WARNING: fix to match camera orientation with piezo orientation
        #self.image = np.rot90(self.image, k=3)
        # send image to gui
        #self.changedImage.emit(self.image) #esta señal va a get_image
        print("image sent to get_image. Type: ", type(self.image))
        self.currentTime = ptime.time() - self.startTime
        
            
    def reset(self):
        if DEBUG:
                print("Inside reset")
        

        self.time = np.zeros(self.npoints)
        self.ptr = 0
        self.startTime = ptime.time()

        print("finishing reset")


    @pyqtSlot()
    def stop(self):
        if DEBUG:
                print("Inside stop")
        
        time.sleep(1)
        
        self.cameraTimer.stop()
        
        #prevent system to throw weird errors when not being able to close the camera, see uc480.py --> close()
#        try:
        self.reset()
#        except:
#            pass
        
        if self.standAlone is True:
            
            # Go back to 0 position
    
            x_0 = 0
            y_0 = 0
            z_0 = 0
    
            
        #self.camera.close()

        print(datetime.now(), '[] program stopped')
        
        # clean up aux files from NiceLib
        
        try:
            os.remove(r'C:\Users\USUARIO\Documents\GitHub\pyflux\lextab.py')
            os.remove(r'C:\Users\USUARIO\Documents\GitHub\pyflux\yacctab.py')
        except:
            pass
        
        
    def make_connection(self, frontend):
        if DEBUG:
                print("Inside make_connection in Backend")

        frontend.closeSignal.connect(self.stop)
        frontend.liveviewButton.clicked.connect(self.liveview)
        print("liveview & liviewbutton connected in backend- line 464")


if __name__ == '__main__':
    if DEBUG:
        print("Inside main")
    
    if not QtGui.QApplication.instance():
        app = QtGui.QApplication([])
    else:
        app = QtGui.QApplication.instance()
        
    #app.setStyle(QtGui.QStyleFactory.create('fusion'))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    print(datetime.now(), 'Module running in stand-alone mode')
    
    ids_peak.Library.Initialize()
    
    # Initialize devices
       
    #if camera wasnt closed properly just keep using it without opening new one

    gui = Frontend()   
    worker = Backend()
    worker.standAlone = True
    
    gui.make_connection(worker)
    worker.make_connection(gui)

    
    # camThread = QtCore.QThread()
    # worker.moveToThread(camThread)
    # worker.cameraTimer.moveToThread(camThread)
    # #worker.cameraTimer.timeout.connect(worker.update) #Esta línea sincroniza el cameraTimer con la ejecución de la función update del Backend
    # worker.cameraTimer.timeout.connect(worker.on_acquisition_timer)
    # print("line 614")
    # camThread.start()

    gui.setWindowTitle('Camera display')
    gui.resize(600, 500)

    gui.show()
    app.exec_()
        