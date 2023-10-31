# -*- coding: utf-8 -*-
"""
Created on Wed Oct  1 13:41:48 2018

@authors: Luciano Masullo modified by Flor C. to use another ROI 
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
sys.path.append('C:\Program Files\Thorlabs\Scientific Imaging\ThorCam')
# install from https://instrumental-lib.readthedocs.io/en/stable/install.html
import tools.viewbox_tools as viewbox_tools
import tools.tools as tools
import tools.PSF as PSF
import tools.colormaps as cmaps
from scipy import optimize as opt

from instrumental.drivers.cameras import uc480
from instrumental import Q_



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
            print("Inside init")

        super().__init__(*args, **kwargs)
        
        self.cropped = False

        self.setup_gui()
        
    @pyqtSlot(bool)        
    def toggle_liveview(self, on):
        if DEBUG:
            print("Inside toggle_liveview")
        if on:
            self.liveviewButton.setChecked(True)
            print(datetime.now(), '[focus] focus live view started')
        else:
            self.liveviewButton.setChecked(False)
            self.img.setImage(np.zeros((512,512)), autoLevels=False)

            print(datetime.now(), '[focus] focus live view stopped - line 202')
            
        
    @pyqtSlot(np.ndarray)
    def get_image(self, img):
        if DEBUG:
            print(" Inside get_image ")
        self.img.setImage(img, autoLevels=False)
                        
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

        
        subgrid.addWidget(self.liveviewButton, 1, 0, 1, 2)

        grid.addWidget(self.paramWidget, 0, 0)

        grid.addWidget(self.camDisplay, 0, 1)
        
        #didnt want to work when being put at earlier point in this function
        self.liveviewButton.clicked.connect(lambda: self.toggle_liveview(self.liveviewButton.isChecked()))
        print("liveviewbutton & toogle liveview connected - line 453")

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
    liveviewSignal = pyqtSignal(bool)


    """
    Signals
    
    - changedImage:
        To: [frontend] get_image

    """

    def __init__(self, camera, *args, **kwargs):
        if DEBUG:
            print("Inside init in backend")
        super().__init__(*args, **kwargs)

        self.camera = camera
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
        
        rawimage = self.camera.latest_frame()
        image = np.sum(rawimage, axis=2)
        
        self.pxSize = 50 #original 10nm FC  # in nm, TODO: check correspondence with GUI
        
        self.sensorSize = np.array(image.shape)
        self.focusSignal = 0
        
        # set focus update rate
        
        self.scansPerS = 10

        self.focusTime = 1000 / self.scansPerS
        self.focusTimer = QtCore.QTimer()
        
        self.reset()
      
        

    
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
        
        if self.camON:
            print("Liveview-start")
            self.camera.stop_live_video()
            self.camON = False
        print("Liveview-start second line")
        self.camON = True
        self.camera.start_live_video()
        self.camera._set_exposure(Q_('5 ms')) #Original THORCAM 50ms
        print("camera started live video mode")

        self.focusTimer.start(self.focusTime)
        print("focus timer started")
        
    def liveview_stop(self):
        if DEBUG:
            print("Inside Liveview-stop")
        self.focusTimer.stop()
        print("focusTimer: stopped")
        self.camON = False
        
        x0 = 0
        y0 = 0
        x1 = 1280 
        y1 = 1024 
            
        val = np.array([x0, y0, x1, y1])
        print("val en liveview_stop:", val)
        self.get_new_roi(val)

           
    def update_stats(self):
        if DEBUG:
                print("Inside update_stats")
        
        # TO DO: fix this function

        signal = self.focusSignal

        if self.n == 1:
            self.mean = signal
            self.mean2 = self.mean**2
        else:
            self.mean += (signal - self.mean)/self.n
            self.mean2 += (signal**2 - self.mean2)/self.n

        # Stats
        self.std = np.sqrt(self.mean2 - self.mean**2)
        self.max_dev = np.max([self.max_dev,
                              self.focusSignal - self.setPoint])
        statData = 'std = {}    max_dev = {}'.format(np.round(self.std, 3),
                                                     np.round(self.max_dev, 3))
        self.gui.focusGraph.statistics.setText(statData)

        self.n += 1
        
    def update(self):
        if DEBUG:
                print("Inside update")
        
        self.acquire_data()
        self.update_graph_data()
        
        #  if locked, correct position
        
        if self.feedback_active:
            
#            self.updateStats()
            self.update_feedback()
            
        if self.save_data_state:
                        
            self.time_array.append(self.currentTime)
            self.z_array.append(self.focusSignal)
            
    def acquire_data(self): #Es update_view en otros códigos
        if DEBUG:
                print("Inside acquire_data")
                
        # acquire image
    
        raw_image = self.camera.latest_frame()

        #image = np.sum(raw_image, axis=2)  #comment FC 28-9 # sum the R, G, B images
        #self.image = raw_image[:, :, 0] #Comment FC para colocar IDS # take only R channel
        self.image = raw_image #Esta linea es para ids, comentar para thorcam
        # WARNING: fix to match camera orientation with piezo orientation
        self.image = np.rot90(self.image, k=3)
        # send image to gui
        self.changedImage.emit(self.image) #esta señal va a get_image
        self.currentTime = ptime.time() - self.startTime
        
    def update_graph_data(self):
        if DEBUG:
                print("Inside update_graph_data")
        ''' update of the data displayed in the gui graph '''

        if self.ptr < self.npoints:
            self.data[self.ptr] = self.focusSignal #Ahora se supone que focusSiganl no es cero
            print("focusSignal in update_graph_data: ", self.focusSignal)
            print("Ya no es cero")
            self.time[self.ptr] = self.currentTime
            
            self.changedData.emit(self.time[0:self.ptr + 1], #Esta señal va a get_data
                                  self.data[0:self.ptr + 1])

        else:
            self.data[:-1] = self.data[1:]
            self.data[-1] = self.focusSignal
            print("focusSignal in update_graph_data (in else): ", self.focusSignal)
            self.time[:-1] = self.time[1:]
            self.time[-1] = self.currentTime

            self.changedData.emit(self.time, self.data)

        self.ptr += 1
  
            
    def reset(self):
        if DEBUG:
                print("Inside reset")
        

        self.time = np.zeros(self.npoints)
        self.ptr = 0
        self.startTime = ptime.time()

        print("focusSignal in reset: ")

        
    def reset_data_arrays(self):
        if DEBUG:
                print("Inside reset_data_arrays")
        
        self.time_array = []
        self.z_array = []
        
  
    @pyqtSlot()    
    def get_stop_signal(self):
        if DEBUG:
                print("Inside get_stop_signal")
        
        """
        From: [psf]
        Description: stops liveview, tracking, feedback if they where running to
        start the psf measurement with discrete xy - z corrections
        """
            
        self.toggle_feedback(False)
        self.toggle_tracking(False)
        
        self.save_data_state = True  # TO DO: sync this with GUI checkboxes (Lantz typedfeat?)
            
        self.reset()
        self.reset_data_arrays()
        
        
  
            
    @pyqtSlot(np.ndarray)
    def get_new_roi(self, val): #This is get_roi_info in other codes
        if DEBUG:
                print("Inside get_new_roi")
        '''
        Connection: [frontend] changedROI
        Description: gets coordinates of the ROI in the GUI
        
        '''
                
        self.ROIcoordinates = val.astype(int)
        print("self.ROIcoordinates", self.ROIcoordinates)
        print("TYPE self.ROIcoordinates", type(self.ROIcoordinates))
        if DEBUG:
            print(datetime.now(), '[focus] got ROI coordinates')
            
       # self.camera._set_AOI(*self.roi_area)
        
       # if DEBUG:
           # print(datetime.now(), '[focus] ROI changed to', self.camera._get_AOI())
    
   

        
    

  
 
        
    @pyqtSlot()
    def stop(self):
        if DEBUG:
                print("Inside stop")
        
        time.sleep(1)
        
        self.focusTimer.stop()
        
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
    
            self.moveTo(x_0, y_0, z_0)
            
        self.camera.close()

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
        frontend.liveviewButton.clicked.connect(self.liveview)
        print("liveview & liviewbutton connected in backend- line 1350")


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
    
    # Initialize devices
       
    #if camera wasnt closed properly just keep using it without opening new one
    try:
        cam = uc480.UC480_Camera()
    except:
        print("Error with cam")
    gui = Frontend()   
    worker = Backend(cam)
    worker.standAlone = True
    
    gui.make_connection(worker)
    worker.make_connection(gui)

    
    focusThread = QtCore.QThread()
    worker.moveToThread(focusThread)
    worker.focusTimer.moveToThread(focusThread)
    worker.focusTimer.timeout.connect(worker.update)
    
    focusThread.start()
    
    # initialize fpar_70, fpar_71, fpar_72 ADwin position parameters
    pos_zero = tools.convert(0, 'XtoU')


    gui.setWindowTitle('Focus lock')
    gui.resize(1500, 500)

    gui.show()
    app.exec_()
        