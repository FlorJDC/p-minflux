﻿# -*- coding: utf-8 -*-
"""
Created on Th Oct  31 2023

@authors: Flor C
Script for image_acquisition using Thorcam
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
            print("Inside init in frontend")

        super().__init__(*args, **kwargs)
        
        self.cropped = False

        self.setup_gui()
        self.cnt =0
        
    @pyqtSlot(bool)        
    def toggle_liveview(self, on):
        if DEBUG:
            print("Inside toggle_liveview")
        if on:
            self.liveviewButton.setChecked(True)
            print(datetime.now(), '[toggle liveview activated] live view started')
        else:
            self.liveviewButton.setChecked(False)
            self.img.setImage(np.zeros((1024,1280)), autoLevels=False)

            print(datetime.now(), '[toggle liveview] live view stopped ')
            
        
    @pyqtSlot(np.ndarray)
    def get_image(self, img):
        if DEBUG:
            print(" Inside get_image ")
        print("image received in get img: ", img, "type: ", type(img), "shape: ", img.shape)
        #---------------------
        mat = np.matrix(img)
        if self.cnt ==0:
            with open('outfile.txt','wb') as f:
                for line in mat:
                    np.savetxt(f, line, fmt='%.2f')
            self.cnt=self.cnt +1
        #------------
        #plt.imshow(img)
        self.img.setImage(img, autoLevels=False) #type self.img:  <class 'pyqtgraph.graphicsItems.ImageItem.ImageItem'>
                        
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
        print("liveviewbutton & toogle liveview connected")

    def closeEvent(self, *args, **kwargs):
        if DEBUG:
            print("Inside closeEvent")
        
        self.closeSignal.emit()
        time.sleep(1)
        
        camThread.exit()
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
        self.camera.master_gain = 4 # Thorcam = 4, IDScam = 1
        self.camera.auto_blacklevel = True  # Comentar para IDS
        self.camera.gain_boost = True # Comentar para IDS
        self.counter =0
        
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

        self.camTime = 1000 / self.scansPerS
        self.cameraTimer = QtCore.QTimer()
        
        self.reset()
      

    @pyqtSlot(bool)
    def liveview(self, value):

        if value:
            self.camON = True
            print("inside Liveview")
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
        self.camera._set_exposure(Q_('50 ms')) #Original THORCAM 50ms #IDS 5ms
        print("camera started live video mode")

        self.cameraTimer.start(self.camTime)
        print("focus timer started")
        
    def liveview_stop(self):
        if DEBUG:
            print("Inside Liveview-stop")
        self.cameraTimer.stop()
        print("cameraTimer: stopped")
        self.camON = False  
        x0 = 0
        y0 = 0
        x1 = 1280 
        y1 = 1024 
            
        val = np.array([x0, y0, x1, y1])
        print("val en liveview_stop:", val)
           
        
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
        self.changedImage.emit(self.image) #esta señal va a get_image
        print("image sent to get_image. Type: ", type(self.image))
        self.counter += 1
        print("contador: ", self.counter)
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
    
            
        self.camera.close()

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

    
    camThread = QtCore.QThread()
    worker.moveToThread(camThread)
    worker.cameraTimer.moveToThread(camThread)
    worker.cameraTimer.timeout.connect(worker.update) #Esta línea sincroniza el cameraTimer con la ejecución de la función update del Backend
    
    camThread.start()

    gui.setWindowTitle('Camera display')
    gui.resize(600, 500)

    gui.show()
    app.exec_()
        