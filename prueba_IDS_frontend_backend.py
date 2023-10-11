# -*- coding: utf-8 -*-
"""
Created on Tue Oct  10 10:41:48 2023

@author: Florencia D. Choque
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

import sys
#sys.path.append('C:\Program Files\Thorlabs\Scientific Imaging\ThorCam') #Comento porque import sys está en mainwindow y parece ir a la ruta indicada sin problemas
#No sabía cuál ruta poner  porque veo dlls en ids_peak en program / generic_sdk /comfort_sdk
# install from https://instrumental-lib.readthedocs.io/en/stable/install.html
import tools.viewbox_tools as viewbox_tools
import tools.tools as tools
import tools.PSF as PSF
import tools.colormaps as cmaps
from scipy import optimize as opt

#from instrumental.drivers.cameras import uc480
#from instrumental import Q_
from ids_peak import ids_peak
from mainwindow import MainWindow
from display import Display
DEBUG = True
FPS_LIMIT = 30


class Frontend(QtGui.QFrame):
    
    if DEBUG:
        print("Inside Frontend")
    changedROI = pyqtSignal(np.ndarray)  # sends new roi size
    closeSignal = pyqtSignal()
    saveDataSignal = pyqtSignal(bool)
    
    paramSignal = pyqtSignal(dict)
    
    """
    Signals
        
    - changedROI: #This is the signal called roiInfoSignal in xy_tracking_2
        To: [backend] get_new_roi #Named get_roi_info in xy_tracking_2
        
    - closeSignal:
        To: [backend] stop
        
    - saveDataSignal:
        To: [backend] get_save_data_state
        
    - paramSignal:
        To: [backend] get_frontend_param

    """
    
    def __init__(self, *args, **kwargs):
        if DEBUG:
            print("Inside init")

        super().__init__(*args, **kwargs)
        
        self.cropped = False

        self.setup_gui()
        
        x0 = 0
        y0 = 0
        x1 = 1280 
        y1 = 1024 
            
        value = np.array([x0, y0, x1, y1])
        self.changedROI.emit(value)
        
    def emit_param(self):
        
        if DEBUG:
            print("Inside emit_param")
        params = dict() #Se crea diccionario vacío FC
        params['pxSize'] = float(self.pxSizeEdit.text())
        print("params:", params, "type param:", type(params))
        
        self.paramSignal.emit(params)

    def roi_method(self):
        if DEBUG:
            print("Inside roi_method")

        ROIpen = pg.mkPen(color='y')
        ROIpos = (512 -64, 512 -64) #cambio FC
        self.roi = viewbox_tools.ROI(140, self.vb, ROIpos,
                                         handlePos=(1, 0),
                                         handleCenter=(0, 1),
                                         scaleSnap=True,
                                         translateSnap=True,
                                         pen=ROIpen)
        self.ROIbutton.setChecked(False)
        self.selectROIbutton.setEnabled(True) #duda: debe ir esto?
        
    def select_roi(self): #Analogo a emit_roi_info
        
        if DEBUG:
            print("Inside select_roi")
        # #self.cropped = True
        # self.getStats = True
        # xmin, ymin = self.roi.pos()
        # xmax, ymax = self.roi.pos() + self.roi.size()
        
        # value = np.array([xmin, xmax, ymin, ymax])  
            
        # #value = np.array([y0, x0, y1, x1])
        # print("Coordinates of the selected roi: ", value)
            
        # self.changedROI.emit(value)
    
        #self.vb.removeItem(self.roi)
        #elf.roi.hide()
        #self.roi = None
        
        #self.vb.enableAutoRange()
        
#    def toggleFocus(self):
#        
#        if self.lockButton.isChecked():
#            
#            self.lockFocusSignal.emit(True)
#
##            self.setpointLine = self.focusGraph.zPlot.addLine(y=self.setPoint, pen='r')
#            
#        else:
#            
#            self.lockFocusSignal.emit(False)
        
#    def delete_roi(self):
#        
#        self.vb.removeItem(self.roi)
#        x0 = 0
#        y0 = 0
#        x1 = 1280 
#        y1 = 1024 
#            
#        value = np.array([x0, y0, x1, y1])
#        self.changedROI.emit(value)
#        self.cropped = False
#        
#        self.roi = None
#        
#        print(datetime.now(), '[focus] ROI deleted')
#        
#        self.deleteROIbutton.setEnabled(False)

    def delete_roi(self):
                
        self.vb.removeItem(self.roi)
        self.roi.hide()
            
    @pyqtSlot(bool)        
    def toggle_liveview(self, on):
        if DEBUG:
            print("Inside toggle_liveview")
        if on:
            self.liveviewButton.setChecked(True)
            print(datetime.now(), '[focus] focus live view started')
        else:
            self.liveviewButton.setChecked(False)
            self.select_roi()
            self.img.setImage(np.zeros((512,512)), autoLevels=False)

            print(datetime.now(), '[focus] focus live view stopped')
            
    @pyqtSlot(np.ndarray)
    def get_image(self, img):
        if DEBUG:
            print(" Inside get_image ")
        self.img.setImage(img, autoLevels=False)
        #croppedimg = img[0:300, 0:300]
        #self.img.setImage(croppedimg)  
                        
    def make_connection(self, backend):
        if DEBUG:
            print("Inside make_connetion")
        backend.changedImage.connect(self.get_image)
        backend.liveviewSignal.connect(self.toggle_liveview)
        print("liveviewSignal connected to toggle liveview - line 318")


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

        # turn ON/OFF feedback loop
        
        self.feedbackLoopBox = QtGui.QCheckBox('Feedback loop')
        
        #shutter button and label
        self.shutterLabel = QtGui.QLabel('Shutter open?')
        self.shutterCheckbox = QtGui.QCheckBox('IR laser')
        
        # Create ROI button
        
        # TODO: completely remove the ROI stuff from the code

        self.ROIbutton = QtGui.QPushButton('ROI')
        self.ROIbutton.setCheckable(True)
        
        # Select ROI
        self.selectROIbutton = QtGui.QPushButton('Select ROI')
        
        # Delete ROI
        self.deleteROIbutton = QtGui.QPushButton('Delete ROI')
        
        self.calibrationButton = QtGui.QPushButton('Calibrate')
        
        self.exportDataButton = QtGui.QPushButton('Export data')
        self.saveDataBox = QtGui.QCheckBox("Save data")
        self.clearDataButton = QtGui.QPushButton('Clear data')
        
        self.pxSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pxSizeEdit = QtGui.QLineEdit('50') #Original: 10nm en focus.py
        self.focusPropertiesDisplay = QtGui.QLabel(' st_dev = 0  max_dev = 0')
        
#        self.deleteROIbutton.setEnabled(False)
#        self.selectROIbutton.setEnabled(False)

        
        # gui connections
        

        self.selectROIbutton.clicked.connect(self.select_roi)
        self.pxSizeEdit.textChanged.connect(self.emit_param)
        self.deleteROIbutton.clicked.connect(self.delete_roi)
        self.ROIbutton.clicked.connect(self.roi_method)

        # focus camera display
        
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
        
        # focus lock graph
        
        self.focusGraph = pg.GraphicsWindow()
        self.focusGraph.setAntialiasing(True)
        
        self.focusGraph.statistics = pg.LabelItem(justify='right')
        self.focusGraph.addItem(self.focusGraph.statistics, row=0, col=0)
        self.focusGraph.statistics.setText('---')
        
        self.focusGraph.zPlot = self.focusGraph.addPlot(row=0, col=0)
        self.focusGraph.zPlot.setLabels(bottom=('Time', 's'),
                                        left=('CM x position', 'px'))
        self.focusGraph.zPlot.showGrid(x=True, y=True)
        self.focusCurve = self.focusGraph.zPlot.plot(pen='r')
 
#        self.focusSetPoint = self.focusGraph.plot.addLine(y=self.setPoint, pen='r')

        # GUI layout
        
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        
        # parameters widget
        
        self.paramWidget = QtGui.QFrame()
        self.paramWidget.setFrameStyle(QtGui.QFrame.Panel |
                                       QtGui.QFrame.Raised)
        #Widget size (widgets with buttons)
        self.paramWidget.setFixedHeight(330)
        self.paramWidget.setFixedWidth(140)
        
        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        
        subgrid.addWidget(self.calibrationButton, 7, 0, 1, 2)
        subgrid.addWidget(self.exportDataButton, 5, 0, 1, 2)
        subgrid.addWidget(self.clearDataButton, 6, 0, 1, 2)
        
        subgrid.addWidget(self.pxSizeLabel, 8, 0)
        subgrid.addWidget(self.pxSizeEdit, 8, 1)
        
        subgrid.addWidget(self.feedbackLoopBox, 9, 0)
        subgrid.addWidget(self.saveDataBox, 10, 0)
        
        #Create button        
        #self.ROIButton = QtGui.QPushButton('ROI')
#        self.ROIButton.setCheckable(True)
#        self.ROIButton.clicked.connect(lambda: self.roi_method())
        
        subgrid.addWidget(self.liveviewButton, 1, 0, 1, 2)
        subgrid.addWidget(self.ROIbutton, 2, 0, 1, 2)
        subgrid.addWidget(self.selectROIbutton, 3, 0, 1, 2)
        subgrid.addWidget(self.deleteROIbutton, 4, 0, 1, 2)
        
        subgrid.addWidget(self.shutterLabel, 11, 0)
        subgrid.addWidget(self.shutterCheckbox, 12, 0)
        
        grid.addWidget(self.paramWidget, 0, 0)
        grid.addWidget(self.focusGraph, 0, 2)
        grid.addWidget(self.camDisplay, 0, 1)
        
        #didnt want to work when being put at earlier point in this function
        self.liveviewButton.clicked.connect(lambda: self.toggle_liveview(self.liveviewButton.isChecked()))
        print("liveviewbutton & toogle liveview connected")

    def closeEvent(self, *args, **kwargs):
        if DEBUG:
            print("Inside closeEvent")
        
        self.closeSignal.emit()
        time.sleep(1)
        
        focusThread.exit()
        super().closeEvent(*args, **kwargs)
        app.quit()
        
        
class Backend(QtCore.QObject):
    if DEBUG:
        print("Inside Backend")
    
    changedImage = pyqtSignal(np.ndarray)
    changedData = pyqtSignal(np.ndarray, np.ndarray)
    changedSetPoint = pyqtSignal(float)
    
    zIsDone = pyqtSignal(bool, float)
    shuttermodeSignal = pyqtSignal(int, bool)
    liveviewSignal = pyqtSignal(bool)
    focuslockpositionSignal = pyqtSignal(float)

    """
    Signals
    
    - changedImage:
        To: [frontend] get_image
             
    - changedData:
        To: [frontend] get_data
        
    - changedSetPoint:
        To: [frontend] get_setpoint
        
    - zIsDone:
        To: [psf] get_z_is_done
        
    - shuttermodeSignal:
        To: [frontend] update_shutter
        
    - focuslockpositionSignal:
        To: [scan] get current focus lock position
        
    """

    def __init__(self, camera, *args, **kwargs):
        if DEBUG:
            print("Inside init in backend")
        super().__init__(*args, **kwargs)

        self.camera = camera #es self.__device #es device_manager.Devices()[0]
        self.standAlone = False
        self.camON = False
        self.roi_area = np.zeros(4)
    
        self.npoints = 400
        
        # checks image size
        
        #rawimage = self.camera.latest_frame()
        #image = np.sum(rawimage, axis=2)
        
        self.pxSize = 50 #original 10nm FC  # in nm, TODO: check correspondence with GUI
        
        #self.sensorSize = np.array(image.shape)
        
        # set focus update rate
        
        self.scansPerS = 10

        self.focusTime = 1000 / self.scansPerS
        self.focusTimer = QtCore.QTimer()
        
        self.nodemap_remote_device = None
        self.datastream = None

        self.__display = None
        self.__acquisition_timer = QtCore.QTimer()
        self.__frame_counter = 0
        self.__error_counter = 0
        self.__acquisition_running = False

        self.__label_infos = None
        self.__label_version = None
        self.__label_aboutqt = None
        
        #These lines open the device
        # Open standard data stream
        datastreams = self.camera.DataStreams()
        if datastreams.empty():
            print("Error", "Device has no DataStream!")

        self.datastream = datastreams[0].OpenDataStream()
        # Get nodemap of the remote device for all accesses to the genicam nodemap tree
        self.nodemap_remote_device = self.camera.RemoteDevice().NodeMaps()[0]
        
        # To prepare for untriggered continuous image acquisition, load the default user set if available and
        # wait until execution is finished
        try:
            self.nodemap_remote_device.FindNode("UserSetSelector").SetCurrentEntry("Default")
            self.nodemap_remote_device.FindNode("UserSetLoad").Execute()
            self.nodemap_remote_device.FindNode("UserSetLoad").WaitUntilDone()
        except ids_peak.Exception:
            # Userset is not available
            pass
        # Get the payload size for correct buffer allocation
        payload_size = self.nodemap_remote_device.FindNode("PayloadSize").Value()

        # Get minimum number of buffers that must be announced
        buffer_count_max = self.datastream.NumBuffersAnnouncedMinRequired()

        # Allocate and announce image buffers and queue them
        for i in range(buffer_count_max):
            buffer = self.datastream.AllocAndAnnounceBuffer(payload_size)
            self.datastream.QueueBuffer(buffer)
        
    @pyqtSlot(dict)
    def get_frontend_param(self, params):
        if DEBUG:
            print("Inside get_frotend_param")
        
        self.pxSize = params['pxSize']
        
        print(datetime.now(), ' [focus] got px size', self.pxSize, ' nm')
         
        
    @pyqtSlot(bool)
    def liveview(self, value):

        if value:
            self.camON = True
            print("Liveview - line 621")
            self.liveview_start()

        else:
            self.liveview_stop()
            self.camON = False

        
    def liveview_start(self):
        try:
            max_fps = self.nodemap_remote_device.FindNode("AcquisitionFrameRate").Maximum()
            print("Max Frame Rate: ", max_fps, "FPS_LIMIT: ", FPS_LIMIT)
            target_fps = min(max_fps, FPS_LIMIT)
            self.nodemap_remote_device.FindNode("AcquisitionFrameRate").SetValue(target_fps)
        except ids_peak.Exception:
            # AcquisitionFrameRate is not available. Unable to limit fps. Print warning and continue on.
            print("Warning","Unable to limit fps, since the AcquisitionFrameRate Node is",target_fps," not supported by the connected camera. Program will continue without limit.")

        # Setup acquisition timer accordingly
        self.focusTimer.setInterval((1 / target_fps) * 1000)
        self.focusTimer.setSingleShot(False)
        #self.__acquisition_timer.timeout.connect(self.on_acquisition_timer)

        try:
            # Lock critical features to prevent them from changing during acquisition
            self.nodemap_remote_device.FindNode("TLParamsLocked").SetValue(1)

            # Start acquisition on camera #Parece que son estas tres lineas
            self.datastream.StartAcquisition()
            self.nodemap_remote_device.FindNode("AcquisitionStart").Execute()
            self.nodemap_remote_device.FindNode("AcquisitionStart").WaitUntilDone()
            
        except Exception as e:
            print("Exception: " + str(e))

        # Start acquisition timer
        self.focusTimer.start()
        #Antes:
        # if self.camON:
        #     print("Liveview-start")
        #     self.camera.stop_capture()
        #     self.camON = False
        # print("Liveview-start second line")
        # self.camON = True
        # self.camera.start_capture()
        # #self.camera.set_exposure_time(Q_('5 ms')) #Original THORCAM 50ms
        # print("camera started live video mode")

        # self.focusTimer.start(self.focusTime)
        # print("focus timer started")
        
    def liveview_stop(self):
        try:
            remote_nodemap = self.camera.RemoteDevice().NodeMaps()[0]
            remote_nodemap.FindNode("AcquisitionStop").Execute()

            # Stop and flush datastream
            self.datastream.KillWait()
            self.datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
            self.datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

            # Unlock parameters after acquisition stop
            if self.nodemap_remote_device is not None:
                try:
                    self.nodemap_remote_device.FindNode("TLParamsLocked").SetValue(0)
                except Exception as e:
                    print("Exception in nodemap_remote_device", str(e))

        except Exception as e:
             print("Exception in liveview_stop", str(e))
        #Antes
        # if DEBUG:
        #     print("Inside Liveview-stop")
        # self.focusTimer.stop()
        # print("focusTimer: stopped")
        # self.camON = False
        
        # x0 = 0
        # y0 = 0
        # x1 = 1280 
        # y1 = 1024 
            
        # val = np.array([x0, y0, x1, y1])
        # print("val en liveview_stop:", val)
                             
    def update(self):
        if DEBUG:
                print("Inside update")
        
        self.acquire_data()

            
    def acquire_data(self): #Es update_view en otros códigos
        if DEBUG:
                print("Inside acquire_data")
                
        # acquire image
    
        self.__display = Display()

        #image = np.sum(raw_image, axis=2)  #comment FC 28-9 # sum the R, G, B images
        #self.image = raw_image[:, :, 0] #Comment FC para colocar IDS # take only R channel
        self.image = self.__display #Esta linea es para ids, comentar para thorcam
        # WARNING: fix to match camera orientation with piezo orientation
        self.image = np.rot90(self.image, k=3)
        # send image to gui
        self.changedImage.emit(self.image) #esta señal va a get_image
        self.currentTime = ptime.time() - self.startTime
     
    @pyqtSlot()    
    def get_lock_signal(self):
        if DEBUG:
                print("Inside get_lock_signal")
        
        if not self.camON:
            self.liveviewSignal.emit(True)
            print("self.liveviewSignal.emit(True) executed in get lock signal")
            
        self.reset_data_arrays()
        
        self.toggle_feedback(True)
        self.toggle_tracking(True)
        self.save_data_state = True
        
        # TO DO: fix updateGUIcheckboxSignal    
        
#        self.updateGUIcheckboxSignal.emit(self.tracking_value, 
#                                          self.feedback_active, 
#                                          self.save_data_state)
        
        print(datetime.now(), '[focus] System focus locked')
               
    @pyqtSlot()
    def stop(self):
        if DEBUG:
                print("Inside stop")
        
        self.focusTimer.stop()
                
        if self.datastream is not None:
            try:
                for buffer in self.datastream.AnnouncedBuffers():
                    self.datastream.RevokeBuffer(buffer)
            except Exception as e:
                print("Exception in stop", str(e))

        print(datetime.now(), '[focus] Focus stopped')
        
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
        frontend.paramSignal.connect(self.get_frontend_param)
        frontend.liveviewButton.clicked.connect(self.liveview)
        print("liveview & liviewbutton connected in backend- line 574")


if __name__ == '__main__':
    if DEBUG:
        print("Inside main")
    
    if not QtGui.QApplication.instance():
        app = QtGui.QApplication([])
    else:
        app = QtGui.QApplication.instance()
        
    #app.setStyle(QtGui.QStyleFactory.create('fusion'))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    print(datetime.now(), '[focus] Focus lock module running in stand-alone mode')
    
    # Initialize device     
    ids_peak.Library.Initialize()
    
    # create a device manager object
    device_manager = ids_peak.DeviceManager.Instance()
    print("Device: ", device_manager)
    try:
        # update the device manager
        device_manager.Update()

        # exit program if no device was found
        if device_manager.Devices().empty():
            print("No device found.")
    except Exception as e:
        print("Exception: " + str(e) + "")
        
    #open selected device
    device = device_manager.Devices()[0] #Es self.__device
    cam = device.OpenDevice(ids_peak.DeviceAccessType_Control) #0 means the first device founded
    
    gui = Frontend()   
    worker = Backend(cam)
    worker.standAlone = True
    
    gui.make_connection(worker)
    worker.make_connection(gui)

    gui.emit_param()
    
    focusThread = QtCore.QThread()
    worker.moveToThread(focusThread)
    worker.focusTimer.moveToThread(focusThread)
    worker.focusTimer.timeout.connect(worker.update)
    
    focusThread.start()
    
    gui.setWindowTitle('Focus lock')
    gui.resize(1500, 500)

    gui.show()
    app.exec_()
        