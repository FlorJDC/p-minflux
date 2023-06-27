# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 10:51:13 2023

@author: Luciano Masullo
Modified to work with new stabilization and ADwin by Florencia D. Choque
Based on xyz_tracking by Luciano Masullo
"""

import numpy as np
import time
import ctypes as ct
import matplotlib.pyplot as plt
from datetime import date, datetime

from scipy import optimize as opt
from PIL import Image

import tools.viewbox_tools as viewbox_tools
import tools.colormaps as cmaps
import tools.PSF as PSF
import tools.tools as tools

import scan

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QGroupBox

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime
import qdarkstyle

from instrumental.drivers.cameras import uc480 #Thorcam FC
from instrumental import Q_
import drivers.ADwin as ADwin

DEBUG = True
DEBUG1 = True

PX_SIZE = 29.0 #px size of camera in nm #antes 80.0 para Andor
PX_Z = 25 # px size for z in nm //Thorcam px size 25nm // IDS px size 50nm 

class Frontend(QtGui.QFrame):
    
    roiInfoSignal = pyqtSignal(int, np.ndarray)
    closeSignal = pyqtSignal()
    saveDataSignal = pyqtSignal(bool)
    
    """
    Signals
             
    - roiInfoSignal:
         To: [backend] get_roi_info
        
    - closeSignal:
         To: [backend] stop
        
    - saveDataSignal:
         To: [backend] get_save_data_state
        
    """
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        
        # initial ROI parameters        
        
        self.ROInumber = 0
        self.roilist = [] #Una lista en la que se guardarán las coordenadas del ROI
        self.roi = None
        
        self.setup_gui()
   
    ############################añado create_roi para xy y z NO SON LINEAS ORIGINALES
    def craete_roi(self, roi_type):
        if DEBUG1:
             print("Estoy en craete_roi")
        if roi_type == 'xy':
        
            ROIpen = pg.mkPen(color='r')
    
            ROIpos = (512 - 64, 512 - 64)
            roi = viewbox_tools.ROI2(50, self.vb, ROIpos, handlePos=(1, 0),
                                     handleCenter=(0, 1),
                                     scaleSnap=True,
                                     translateSnap=True,
                                     pen=ROIpen, number=self.ROInumber)
            
            self.ROInumber += 1
            self.roilist.append(roi)
            self.xyROIButton.setChecked(False)
            
        if roi_type == 'z':
            
            ROIpen = pg.mkPen(color='y')
            
            ROIpos = (512 - 64, 512 - 64)
            self.roi_z = viewbox_tools.ROI2(140, self.vb, ROIpos,
                                            handlePos=(1, 0),
                                            handleCenter=(0, 1),
                                            scaleSnap=True,
                                            translateSnap=True,
                                            pen=ROIpen, number=self.ROInumber)
            
            self.zROIButton.setChecked(False)
    ######################################################################añado emit_roi_info para xy y z NO SON LINEAS ORIGINALES
    def emit_roi_info(self, roi_type):
        
        if DEBUG1:
             print("Estoy en emit_roi_info")
        
        if roi_type == 'xy':
        
            roinumber = len(self.roilist)
            
            if roinumber == 0:
                
                print(datetime.now(), '[xy_tracking] Please select a valid ROI for fiducial NPs tracking')
                
            else:
                
                coordinates = np.zeros((4))
                coordinates_list = []
                
                for i in range(len(self.roilist)):
                    
                    xmin, ymin = self.roilist[i].pos()
                    xmax, ymax = self.roilist[i].pos() + self.roilist[i].size()
            
                    coordinates = np.array([xmin, xmax, ymin, ymax])  
                    coordinates_list.append(coordinates)
                                                            
                self.roiInfoSignal.emit('xy', roinumber, coordinates_list)
                    
        if roi_type == 'z':
            
            xmin, ymin = self.roi_z.pos()
            xmax, ymax = self.roi_z.pos() + self.roi_z.size()
            
            coordinates = np.array([xmin, xmax, ymin, ymax]) 
            coordinates_list = [coordinates]
            
            self.z_roiInfoSignal.emit('z', 0, coordinates_list)
            
        if DEBUG1:
                print("roiInfoSignal.emit executed, signal from Frontend (function:emit_roi_info, to Backend:get_roi info FC")

    def delete_roi_z(self): #elimina todas las ROI de la lista, antes era delete_roi
        if DEBUG1:
            print("EStoy en delete_roi_z")
        
        for i in range(len(self.roi_z)):
            
            self.vb.removeItem(self.roi_z)
            self.roi_z.hide()
            
        self.roi_z = []
        self.delete_roiButton.setChecked(False)
        self.ROInumber = 0
    
    def delete_roi(self): #elimina solo la última ROI
                
        if DEBUG1:
            print("EStoy en delete_roi")
        self.vb.removeItem(self.roilist[-1])
        self.roilist[-1].hide()
        self.roilist = self.roilist[:-1]
        self.ROInumber -= 1
     
    @pyqtSlot(bool) #no toco esta función FC
    def toggle_liveview(self, on):
        if DEBUG1:
            print("EStoy en toggle_liveview")

        if on:
            self.liveviewButton.setChecked(True)
            print(datetime.now(), '[xy_tracking] Live view started')
        else:
            self.liveviewButton.setChecked(False)
            self.emit_roi_info()
            self.img.setImage(np.zeros((512, 512)), autoLevels=False)
            print(datetime.now(), '[xy_tracking] Live view stopped')
        
    @pyqtSlot()  
    def get_roi_request(self):
        if DEBUG1:
            print("Estoy en get_roi_request")
        
        print(datetime.now(), '[xy_tracking] got ROI request')
        
        self.emit_roi_info()
        
    @pyqtSlot(np.ndarray)
    def get_image(self, img):
        
#        if DEBUG:
#            print(datetime.now(),'[xy_tracking-frontend] got image signal')

        self.img.setImage(img, autoLevels=False)
        
        self.xaxis.setScale(scale=PX_SIZE/1000) #scale to µm
        self.yaxis.setScale(scale=PX_SIZE/1000) #scale to µm
        
        
    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def get_data(self, time, xData, yData):
        
        print("xData: ",xData)
        print("yData: ",yData)
        print("time: ",time)
        self.xCurve.setData(time, xData)
        self.yCurve.setData(time, yData)
        
        self.xyDataItem.setData(yData, xData) #Cambié el orden de los parámetros para que el grafico quede bien 5-6 FC
        
        if len(xData) > 2:
            
            self.plot_ellipse(xData, yData)
            #####################################
            #Agrego estas lineas de prueba std FC
            
            meanX = np.mean(xData,axis=None)
            print("mean x" ,np.mean(xData,axis=None))
            xstd = np.std(xData)
            print("stdx", xstd)
            self.xstd_value.setText(str(np.around(xstd, 2)))
            print("std_value x",self.xstd_value)
            
            ystd = np.std(yData)
            print("stdy",ystd)
            self.ystd_value.setText(str(np.around(ystd, 2)))
            #########################################
        
    def plot_ellipse(self, x_array, y_array):
        
        pass
        
#            cov = np.cov(x_array, y_array)
#            
#            a, b, theta = tools.cov_ellipse(cov, q=.683)
#            
#            theta = theta + np.pi/2            
##            print(a, b, theta)
#            
#            xmean = np.mean(xData)
#            ymean = np.mean(yData)
#            
#            t = np.linspace(0, 2 * np.pi, 1000)
#            
#            c, s = np.cos(theta), np.sin(theta)
#            R = np.array(((c, -s), (s, c)))
#            
#            coord = np.array([a * np.cos(t), b * np.sin(t)])
#            
#            coord_rot = np.dot(R, coord)
#            
#            x = coord_rot[0] + xmean
#            y = coord_rot[1] + ymean
            
            # TO DO: fix plot of ellipse
            
#            self.xyDataEllipse.setData(x, y)
#            self.xyDataMean.setData([xmean], [ymean])

    @pyqtSlot(int, bool)    
    def update_shutter(self, num, on):
        
        '''
        setting of num-value:
            0 - signal send by scan-gui-button --> change state of all minflux shutters
            1...6 - shutter 1-6 will be set according to on-variable, i.e. either true or false; only 1-4 controlled from here
            7 - set all minflux shutters according to on-variable
            8 - set all shutters according to on-variable
        for handling of shutters 1-5 see [scan] and [focus]
        '''
        
        if (num == 6)  or (num == 8):
            self.shutterCheckbox.setChecked(on)
                    
    @pyqtSlot(bool, bool, bool)
    def get_backend_states(self, tracking, feedback, savedata):

        self.trackingBeadsBox.setChecked(tracking)
        self.feedbackLoopBox.setChecked(feedback)
        self.saveDataBox.setChecked(savedata)            

    def emit_save_data_state(self):
        
        if self.saveDataBox.isChecked():
            
            self.saveDataSignal.emit(True)
            self.emit_roi_info()
            
        else:
            
            self.saveDataSignal.emit(False)
        
    def make_connection(self, backend):
            
        backend.changedImage.connect(self.get_image)
        backend.changedData.connect(self.get_data)
        backend.updateGUIcheckboxSignal.connect(self.get_backend_states)
        backend.shuttermodeSignal.connect(self.update_shutter)
        backend.liveviewSignal.connect(self.toggle_liveview)
        print("liveviewSignal connected to toggle liveview - line 249")
        
    def setup_gui(self):
        
        # GUI layout
        
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        
        # parameters widget
        
        self.paramWidget = QGroupBox('XY-Tracking parameter')   
        self.paramWidget.setFixedHeight(260)
        self.paramWidget.setFixedWidth(250)
        
        grid.addWidget(self.paramWidget, 0, 1)
        
        #################################
        # stats widget
        
        self.statWidget = QGroupBox('Live statistics')   
        self.statWidget.setFixedHeight(200)
        # self.statWidget.setFixedWidth(240)
        self.statWidget.setFixedWidth(250)

        self.xstd_label = QtGui.QLabel('X std (nm)')
        self.ystd_label = QtGui.QLabel('Y std (nm)')
        #self.zstd_label = QtGui.QLabel('Z std (nm)')
        
        self.xstd_value = QtGui.QLabel('0')
        self.ystd_value = QtGui.QLabel('0')
        #self.zstd_value = QtGui.QLabel('0')
        #################################
        # image widget layout
        
        imageWidget = pg.GraphicsLayoutWidget()
        imageWidget.setMinimumHeight(400)
        imageWidget.setMinimumWidth(400)
        
        # setup axis, for scaling see get_image()
        self.xaxis = pg.AxisItem(orientation='bottom', maxTickLength=5)
        self.xaxis.showLabel(show=True)
        self.xaxis.setLabel('x', units='µm')
        
        self.yaxis = pg.AxisItem(orientation='left', maxTickLength=5)
        self.yaxis.showLabel(show=True)
        self.yaxis.setLabel('y', units='µm')
        
        self.vb = imageWidget.addPlot(axisItems={'bottom': self.xaxis, 
                                                 'left': self.yaxis})
    
        self.vb.setAspectLocked(True)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        grid.addWidget(imageWidget, 0, 0)
        
        # set up histogram for the liveview image

        self.hist = pg.HistogramLUTItem(image=self.img)
        
       # lut = viewbox_tools.generatePgColormap(cmaps.parula) #chequear que hacen
       # self.hist.gradient.setColorMap(lut) #
       
#        self.hist.vb.setLimits(yMin=800, yMax=3000)

        ## TO DO: fix histogram range


        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=0, col=1)
        
        # xy drift graph (graph without a fixed range)
        
        self.xyGraph = pg.GraphicsWindow()
    
#        self.xyGraph.resize(200, 300)
        self.xyGraph.setAntialiasing(True)
        
        self.xyGraph.statistics = pg.LabelItem(justify='right')
        self.xyGraph.addItem(self.xyGraph.statistics)
        self.xyGraph.statistics.setText('---')
        
        self.xyGraph.xPlot = self.xyGraph.addPlot(row=1, col=0)
        self.xyGraph.xPlot.setLabels(bottom=('Time', 's'),
                            left=('Y position', 'nm'))   # TO DO: clean-up the x-y mess (they're interchanged)
        self.xyGraph.xPlot.showGrid(x=True, y=True)
        self.xCurve = self.xyGraph.xPlot.plot(pen='b')
        

        
        self.xyGraph.yPlot = self.xyGraph.addPlot(row=0, col=0)
        self.xyGraph.yPlot.setLabels(bottom=('Time', 's'),
                                     left=('X position', 'nm'))
        self.xyGraph.yPlot.showGrid(x=True, y=True)
        self.yCurve = self.xyGraph.yPlot.plot(pen='r')
        
        # xy drift graph (2D point plot)
        
        self.xyPoint = pg.GraphicsWindow()
        self.xyPoint.resize(400, 400)
        self.xyPoint.setAntialiasing(False)
        
#        self.xyPoint.xyPointPlot = self.xyGraph.addPlot(col=1)
#        self.xyPoint.xyPointPlot.showGrid(x=True, y=True)
        
        self.xyplotItem = self.xyPoint.addPlot()
        self.xyplotItem.showGrid(x=True, y=True)
        self.xyplotItem.setLabels(bottom=('X position', 'nm'),
                                  left=('Y position', 'nm'))#Cambio ejes FC
        self.xyplotItem.setAspectLocked(True) #Agregué FC
        
        self.xyDataItem = self.xyplotItem.plot([], pen=None, symbolBrush=(255,0,0), 
                                               symbolSize=5, symbolPen=None)
        
        self.xyDataMean = self.xyplotItem.plot([], pen=None, symbolBrush=(117, 184, 200), 
                                               symbolSize=5, symbolPen=None)
        
        self.xyDataEllipse = self.xyplotItem.plot(pen=(117, 184, 200))

        
        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('Camera LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        
        # create ROI button
    
        self.ROIButton = QtGui.QPushButton('ROI')
        self.ROIButton.setCheckable(True)
        self.ROIButton.clicked.connect(self.craete_roi)
        
        # select ROI
        
        self.selectROIbutton = QtGui.QPushButton('Select ROI')
        self.selectROIbutton.clicked.connect(self.emit_roi_info)
        
        # delete ROI button
        
        self.delete_roiButton = QtGui.QPushButton('delete ROIs')
        self.delete_roiButton.clicked.connect(self.delete_roi)
        
        # position tracking checkbox
        
        self.exportDataButton = QtGui.QPushButton('export current data')

        # position tracking checkbox
        
        self.trackingBeadsBox = QtGui.QCheckBox('Track xy fiducials')
        self.trackingBeadsBox.stateChanged.connect(self.emit_roi_info)
        ################################################me parece que aquí falta una linea (cf xyz_tracking_flor)
        
        # turn ON/OFF feedback loop
        
        self.feedbackLoopBox = QtGui.QCheckBox('Feedback loop')

        # save data signal
        
        self.saveDataBox = QtGui.QCheckBox("Save data")
        self.saveDataBox.stateChanged.connect(self.emit_save_data_state)
        
        
        # button to clear the data
        
        self.clearDataButton = QtGui.QPushButton('Clear data')
        
        #shutter button and label
        self.shutterLabel = QtGui.QLabel('Shutter open?')
        self.shutterCheckbox = QtGui.QCheckBox('473 nm laser')

        # LiveView Button

        self.xyPatternButton = QtGui.QPushButton('Move')
        
        # buttons and param layout
        
        ####################### FC
        grid.addWidget(self.paramWidget, 0, 1)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.statWidget, 0, 2)
        #########################
        
        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)

        subgrid.addWidget(self.liveviewButton, 0, 0)
        subgrid.addWidget(self.ROIButton, 1, 0)
        subgrid.addWidget(self.selectROIbutton, 2, 0)
        subgrid.addWidget(self.delete_roiButton, 3, 0)
        subgrid.addWidget(self.exportDataButton, 4, 0)
        subgrid.addWidget(self.clearDataButton, 5, 0)
        subgrid.addWidget(self.trackingBeadsBox, 1, 1)
        subgrid.addWidget(self.feedbackLoopBox, 2, 1)
        subgrid.addWidget(self.saveDataBox, 3, 1)
        subgrid.addWidget(self.shutterLabel, 7, 0)
        subgrid.addWidget(self.shutterCheckbox, 7, 1)
        subgrid.addWidget(self.xyPatternButton, 9, 0)
        
        ####################################################
        #Agrego FC
        stat_subgrid = QtGui.QGridLayout()
        self.statWidget.setLayout(stat_subgrid)
        
        stat_subgrid.addWidget(self.xstd_label, 0, 0)
        stat_subgrid.addWidget(self.ystd_label, 1, 0)
        #stat_subgrid.addWidget(self.zstd_label, 2, 0)
        stat_subgrid.addWidget(self.xstd_value, 0, 1)
        stat_subgrid.addWidget(self.ystd_value, 1, 1)
        #stat_subgrid.addWidget(self.zstd_value, 2, 1)
        ########################################################
        
        grid.addWidget(self.xyGraph, 1, 0)
        grid.addWidget(self.xyPoint, 1, 1,1,2) #######agrego 1,2 al final
        
        self.liveviewButton.clicked.connect(lambda: self.toggle_liveview(self.liveviewButton.isChecked()))
        print("liveviewButton connected to toggle liveview - line 431")
        
    def closeEvent(self, *args, **kwargs):
        
        self.closeSignal.emit()
        super().closeEvent(*args, **kwargs)
        app.quit()
        
class Backend(QtCore.QObject):
    
    changedImage = pyqtSignal(np.ndarray)
    changedData = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    updateGUIcheckboxSignal = pyqtSignal(bool, bool, bool) #no se usa en xyz_tracking

    xyIsDone = pyqtSignal(bool, float, float)  # signal to emit new piezo position after drift correction
    shuttermodeSignal = pyqtSignal(int, bool)
    liveviewSignal = pyqtSignal(bool)
    """
    Signals
    
    - changedImage:
        To: [frontend] get_image
             
    - changedData:
        To: [frontend] get_data
        
    - updateGUIcheckboxSignal:
        To: [frontend] get_backend_states
        
    - xyIsDone:
        To: [psf] get_xy_is_done
        
    - shuttermodeSignal:
        To: [frontend] update_shutter

    """

    def __init__(self, thorcam, adw, *args, **kwargs): #cambié andor por thorcam
        super().__init__(*args, **kwargs)
        
        #self.andor = andor #andor debe ser inicializada
        #self.initialize_camera()
        #self.setup_camera()
        
        self.camera = thorcam # no need to setup or initialize camera
        self.camera.master_gain = 4 #a estas líneas las saqué de xyz_tacking
        self.camera.auto_blacklevel = True
        self.camera.gain_boost = True
        
        self.adw = adw
        # folder
        
        today = str(date.today()).replace('-', '')  # TO DO: change to get folder from microscope
        root = r'C:\\Data\\'
        folder = root + today
        print("Name of folder: ",folder)
        
        filename = r'\xydata'
        self.filename = folder + filename
        
        self.viewtimer = QtCore.QTimer() #Ojo: aquí coloqué viewtimer porque es el que se usa a lo largo del código, pero en xyz_tracking se usa view_timer
        #self.viewtimer.timeout.connect(self.update) #Línea original
        self.xy_time = 200 # 200 ms per acquisition + fit + correction
        
        self.tracking_value = False
        self.save_data_state = False
        self.feedback_active = False
        self.camON = False

        self.npoints = 1200
        self.buffersize = 30000
        
        self.currentx = 0
        self.currenty = 0
        
        #self.reset() #comwnté FC
       # self.reset_data_arrays() #comenté FC
        
        self.counter = 0
        
        # saves displacement when offsetting setpoint for feedbackloop
        
        self.displacement = np.array([0.0, 0.0])
        self.pattern = False
       
    @pyqtSlot(int, bool)
    def toggle_tracking_shutter(self, num, val):
        #TODO: change code to also update checkboxes in case of minflux measurement
        if (num == 6)  or (num == 8):
            if val:
                tools.toggle_shutter(self.adw, 6, True)
                print(datetime.now(), '[xy_tracking] Tracking shutter opened')
            else:
                tools.toggle_shutter(self.adw, 6, False)
                print(datetime.now(), '[xy_tracking] Tracking shutter closed')
   
    @pyqtSlot(int, bool)
    def shutter_handler(self, num, on):
        self.shuttermodeSignal.emit(num, on)
        
    @pyqtSlot(bool)
    def liveview(self, value):
        
        '''
        Connection: [frontend] liveviewSignal
        Description: toggles start/stop the liveview of the camera.
        
        '''
        print("debugging liveview, value is:",value)
        if value:
            self.camON = True
            print(self.camON)
            self.liveview_start()
            print("arrancó liveview")
            
        else:
            print("estoy en el else")
            self.liveview_stop()
            print("pasò el liveview_stop")
            self.camON = False #esta línea es necesaria? porque 


    def liveview_start(self): #Esto es como en xyz_tracking - focus

        if self.camON:
            print("linea 551")
            self.camera.stop_live_video()
            print("linea 553")
            self.camON = False
        
        print("línea 556")
        self.camON = True
        print("linea 557")
        self.camera.start_live_video()
        self.camera._set_exposure(Q_('50 ms')) # ms # 50 ms Thorcam, 5ms IDS cam
        ET = self.camera._get_exposure() #añadidas por FLOR E
        print('ET='+str(ET)) #añadidas por FLOR E
        #self.camera.start_live_video(framerate='20 Hz') #lìnea original de -flor C
        #print("linea 559")
        self.viewtimer.start(self.xy_time)
    
    def liveview_stop(self):
                
        self.viewtimer.stop()
        print("viewtimer stop")
        self.camON = False
        
        x0 = 0
        y0 = 0
        x1 = 1280 
        y1 = 1024 
            
        val = np.array([x0, y0, x1, y1])
        #self.get_new_roi(val) #¿debo comentar esta línea como se hizo en xyz_tracking.py?
        #SI, Aquì no existe la funciòn get_new_roi como en focus.py
                    
    def update(self):
        """ General update method """
        
     #   print(datetime.now(), '[xy_tracking] entered update')
        
        self.update_view()

        if self.tracking_value:
            
            t0 = time.time()
            self.track('xy')
            t1 = time.time()
        
            print('track xy took', (t1-t0)*1000, 'ms')
            
            t0 = time.time()
            self.track('z')
            t1 = time.time()
            
            print('track z took', (t1-t0)*1000, 'ms')
            
            t0 = time.time()
            self.update_graph_data()
            t1 = time.time()
            
            print('update graph data took', (t1-t0)*1000, 'ms')
            
            if self.feedback_active:
                    
                t0 = time.time()    
                self.correct()
                t1 = time.time()
                
                print('correct took', (t1-t0)*1000, 'ms')
                
        if self.pattern:
            val = (self.counter - self.initcounter)
            reprate = 50 #Antes era 10 para andor
            if (val % reprate == 0):
                self.make_tracking_pattern(val//reprate)
            
        self.counter += 1  # counter to check how many times this function is executed



    def update_view(self):
        """ Image update while in Liveview mode """
        
        # acquire image
        #print("Estoy dentro del update_view")
        raw_image = self.camera.latest_frame()
        #print("Lìnea 613")
        #self.image = np.sum(raw_image, axis=2)   # sum the R, G, B images
        self.image = raw_image[:, :, 0]
        #print("Lìnea 616")
        # WARNING: fix to match camera orientation with piezo orientation
        self.image = np.rot90(self.image, k=3) #Comment by FC
        #print("Lìnea 619")

        # send image to gui
        self.changedImage.emit(self.image)
        #print("Lìnea 623")
        
        
    def update_graph_data(self):
        """ Update the data displayed in the graphs """
        
        if self.ptr < self.npoints:
            self.xData[self.ptr] = self.x + self.displacement[0]
            self.yData[self.ptr] = self.y + self.displacement[1]
            self.time[self.ptr] = self.currentTime
            
            self.changedData.emit(self.time[0:self.ptr + 1],
                                  self.xData[0:self.ptr + 1],
                                  self.yData[0:self.ptr + 1])

        else:
            self.xData[:-1] = self.xData[1:]
            self.xData[-1] = self.x + self.displacement[0]
            self.yData[:-1] = self.yData[1:]
            self.yData[-1] = self.y + self.displacement[1]
            self.time[:-1] = self.time[1:]
            self.time[-1] = self.currentTime
            
            self.changedData.emit(self.time, self.xData, self.yData)

        self.ptr += 1
    
    @pyqtSlot(bool)
    def toggle_tracking(self, val): #esta función es igual a la de xyz_tracking porque es para xy únicamente
        
        '''
        Connection: [frontend] trackingBeadsBox.stateChanged
        Description: toggles ON/OFF tracking of fiducial fluorescent beads. 
        Drift correction feedback loop is not automatically started.
        
        '''

        
        self.startTime = time.time()
        
        if val is True:
            
            self.reset()
            self.reset_data_arrays()
            
            self.tracking_value = True
            self.counter = 0
            
            # initialize relevant xy-tracking arrays 
        
            size = len(self.roi_coordinates_list)
            
            self.currentx = np.zeros(size)
            self.currenty = np.zeros(size)
            self.x = np.zeros(size)
            self.y = np.zeros(size)
            
            if self.initial is True:
                
                self.initialx = np.zeros(size)
                self.initialy = np.zeros(size)
                    
        if val is False:
        
            self.tracking_value = False
            
    @pyqtSlot(bool)
    def toggle_feedback(self, val, mode='continous'):
        ''' 
        Connection: [frontend] feedbackLoopBox.stateChanged
        Description: toggles ON/OFF feedback for either continous (TCSPC) 
        or discrete (scan imaging) correction
        '''
        
        if val is True:
            
            self.feedback_active = True

            # set up and start actuator process
            
            if mode == 'continous':
            
                self.set_actuator_param()
                self.adw.Start_Process(4)
                print('process 4 status', self.adw.Process_Status(4))
                print(datetime.now(), '[focus] Process 4 started')
            
            if DEBUG:
                print(datetime.now(), '[xy_tracking] Feedback loop ON')
            
        if val is False:
            
            self.feedback_active = False
            
            if mode == 'continous':

                self.adw.Stop_Process(4)
                print(datetime.now(), '[xy_tracking] Process 4 stopped')
                self.displacement = np.array([0.0, 0.0])

            
            if DEBUG:
                print(datetime.now(), '[xy_tracking] Feedback loop OFF')
#            
#        self.updateGUIcheckboxSignal.emit(self.tracking_value, 
#                                          self.feedback_active, 
#                                          self.save_data_state)
            
    def gaussian_fit(self,roi_coordinates): #Le estoy agregando un parámetro (roi_coordinates) para que sea como en xyz_tracking
        
        # set main reference frame
        
        roi_coordinates = np.array(roi_coordinates, dtype=np.int)
        
        xmin, xmax, ymin, ymax = roi_coordinates
        xmin_nm, xmax_nm, ymin_nm, ymax_nm = roi_coordinates * PX_SIZE
        
        # select the data of the image corresponding to the ROI

        array = self.image[xmin:xmax, ymin:ymax]
        
        if np.size(array) == 0:
            
            print('WARNING: array is []')
        
        # set new reference frame
        
        xrange_nm = xmax_nm - xmin_nm
        yrange_nm = ymax_nm - ymin_nm
             
        x_nm = np.arange(0, xrange_nm, PX_SIZE)
        y_nm = np.arange(0, yrange_nm, PX_SIZE)
        
        (Mx_nm, My_nm) = np.meshgrid(x_nm, y_nm)
        
        # find max 
        
        argmax = np.unravel_index(np.argmax(array, axis=None), array.shape)
        
        x_center_id = argmax[0]
        y_center_id = argmax[1]
        
        # define area around maximum
    
        xrange = 15 # in px #en el código original era 10, pero lo cambié porque así está en xyz_tracking
        yrange = 15 # in px
        
        xmin_id = int(x_center_id-xrange)
        xmax_id = int(x_center_id+xrange)
        
        ymin_id = int(y_center_id-yrange)
        ymax_id = int(y_center_id+yrange)
        
        array_sub = array[xmin_id:xmax_id, ymin_id:ymax_id]
                
        xsubsize = 2 * xrange
        ysubsize = 2 * yrange
        
#        plt.imshow(array_sub, cmap=cmaps.parula, interpolation='None')
        
        x_sub_nm = np.arange(0, xsubsize) * PX_SIZE
        y_sub_nm = np.arange(0, ysubsize) * PX_SIZE

        [Mx_sub, My_sub] = np.meshgrid(x_sub_nm, y_sub_nm)
        
        # make initial guess for parameters
        
        bkg = np.min(array)
        A = np.max(array) - bkg
        σ = 200 # nm #antes era 130nm
        x0 = x_sub_nm[int(xsubsize/2)]
        y0 = y_sub_nm[int(ysubsize/2)]
        
        initial_guess_G = [A, x0, y0, σ, σ, bkg]
        
        if np.size(array_sub) == 0:
            
            print('WARNING: array_sub is []')
         
        poptG, pcovG = opt.curve_fit(PSF.gaussian2D, (Mx_sub, My_sub), 
                                     array_sub.ravel(), p0=initial_guess_G)
        
        perr = np.sqrt(np.diag(pcovG))
        
        print('perr', perr)
        
        # retrieve results

        poptG = np.around(poptG, 2)
    
        A, x0, y0, σ_x, σ_y, bkg = poptG
        
        x = x0 + Mx_nm[xmin_id, ymin_id]
        y = y0 + My_nm[xmin_id, ymin_id]
        
        currentx = x
        currenty = y
        
        # if to avoid (probably) false localizations #notar que esta parte no se usa en xyz_tracking
        
        maxdist = 200 # in nm
        
        if self.initial is False:
        
            if np.abs(x - self.currentx) < maxdist and np.abs(y - self.currenty) < maxdist:
        
                self.currentx = x
                self.currenty = y
                
#                print(datetime.now(), '[xy_tracking] normal')
                
            else:
                
                pass
                
                print(datetime.now(), '[xy_tracking] max dist exceeded')
        
        else:
            
             return currentx, currenty
            
#            print(datetime.now(), '[xy_tracking] else')
        
            
    def track(self, track_type): #Añado parámetro para trabajar en xy y z
        
        """ 
        Function to track fiducial markers (Au NPs) from the selected ROI.
        The position of the NPs is calculated through an xy gaussian fit 
        If feedback_active = True it also corrects for drifts in xy
        If save_data_state = True it saves the xy data
        
        """
        
        # Calculate average intensity in the image to check laser fluctuations
        
        self.avgInt = np.mean(self.image)
        
        print('Average intensity', self.avgInt)
        
        # xy track routine of N=size fiducial AuNP

        if track_type == 'xy':
            
            for i, roi in enumerate(self.roi_coordinates_list):
                
                # try:
                #     roi = self.roi_coordinates_list[i]
                #     self.currentx[i], self.currenty[i] = self.gaussian_fit(roi)
                    
                # except(RuntimeError, ValueError):
                    
                #     print(datetime.now(), '[xy_tracking] Gaussian fit did not work')
                #     self.toggle_feedback(False)
                
                roi = self.roi_coordinates_list[i]
                self.currentx[i], self.currenty[i] = self.gaussian_fit(roi)
           
            if self.initial is True:
                
                for i, roi in enumerate(self.roi_coordinates_list):
                       
                    self.initialx[i] = self.currentx[i]
                    self.initialy[i] = self.currenty[i]
                    
                self.initial = False
            
            for i, roi in enumerate(self.roi_coordinates_list):
                    
                self.x[i] = self.currentx[i] - self.initialx[i]  # self.x is relative to initial pos
                self.y[i] = self.currenty[i] - self.initialy[i]
                
                self.currentTime = time.time() - self.startTime
                
            # print('x, y', self.x, self.y)
            # print('currentx, currenty', self.currentx, self.currenty)
                
            if self.save_data_state:
                
                self.time_array[self.j] = self.currentTime
                self.x_array[self.j, :] = self.x + self.displacement[0]
                self.y_array[self.j, :] = self.y + self.displacement[1]
                
                self.j += 1
                            
                if self.j >= (self.buffersize - 5):    # TODO: -5, arbitrary bad fix
                    
                    self.export_data()
                    self.reset_data_arrays()
                    
            #         print(datetime.now(), '[xy_tracking] Data array, longer than buffer size, data_array reset')
            
        # z track of the reflected IR beam   
        ####################### Revisar esto del trackeo en z, no puedo correlacionar con focus.py
            
        if track_type == 'z':
            
            self.center_of_mass()
            
            if self.initial_focus is True:
                
                self.initialz = self.currentz
                
                self.initial_focus = False
            
            self.z = (self.currentz - self.initialz) * PX_Z
                
    def correct(self, mode='continous'):

        dx = 0
        dy = 0
        threshold = 3 #antes era 5
        far_threshold = 12
        correct_factor = 0.6
        security_thr = 0.35 # in µm
        
        if np.abs(self.x) > threshold:
            
            dx = - (self.x)/1000 # conversion to µm
            
            if dx < far_threshold:
                
                dx = correct_factor * dx
            
            #  print('dx', dx)
            
        if np.abs(self.y) > threshold:
            
            dy = - (self.y)/1000 # conversion to µm
            
            if dy < far_threshold:
                
                dy = correct_factor * dy
            
#                print('dy', dy)
    
        if dx > security_thr or dy > security_thr:
            
            print(datetime.now(), '[xy_tracking] Correction movement larger than 200 nm, active correction turned OFF')
            self.toggle_feedback(False)
            
        else:
            
            # compensate for the mismatch between camera/piezo system of reference
            
            theta = np.radians(-3.7)   # 86.3 (or 3.7) is the angle between camera and piezo (measured)
            c, s = np.cos(theta), np.sin(theta)
            R = np.array(((c,-s), (s, c)))
            
            dy, dx = np.dot(R, np.asarray([dx, dy]))
            
            # add correction to piezo position
            
            currentXposition = tools.convert(self.adw.Get_FPar(70), 'UtoX')
            currentYposition = tools.convert(self.adw.Get_FPar(71), 'UtoX')

            targetXposition = currentXposition + dx  
            targetYposition = currentYposition + dy  
            
            if mode == 'continous':
            
                self.actuator_xy(targetXposition, targetYposition)
                
            if mode == 'discrete':
                
#                self.moveTo(targetXposition, targetYposition, 
#                            currentZposition, pixeltime=10)
                
                self.target_x = targetXposition
                self.target_y = targetYposition
            
    @pyqtSlot(bool, bool)
    def single_xy_correction(self, feedback_val, initial): #¿Es necesaria esta función? o está incluida en update()
        
        """
        From: [psf] xySignal
        Description: Starts acquisition of the camera and makes one single xy
        track and, if feedback_val is True, corrects for the drift
        """
        if DEBUG:
            print(datetime.now(), '[xy_tracking] Feedback {}'.format(feedback_val))
        
        if initial:
            self.toggle_feedback(True, mode='discrete')
            self.initial = initial
            print(datetime.now(), '[xy_tracking] initial', initial)
        
        if not self.camON:
            print(datetime.now(), 'liveview started')
            self.camON = True
            self.camera.start_live_video(framerate='20 Hz')
            time.sleep(0.200)
            
        time.sleep(0.200)
        print("Estoy dentro de single_xy_correction")
        raw_image = self.camera.latest_frame()
        self.image = raw_image[:, :, 0]
        self.changedImage.emit(self.image)
            
        self.camera.stop_live_video()
        self.camON = False
        
        self.track('xy')
        self.update_graph_data()
        self.correct(mode='discrete')
                
        target_x = np.round(self.target_x, 3)
        target_y = np.round(self.target_y, 3)
        
        print(datetime.now(), '[xy_tracking] discrete correction to', 
              target_x, target_y)
    
        self.xyIsDone.emit(True, target_x, target_y)
        
        if DEBUG:
            print(datetime.now(), '[xy_tracking] single xy correction ended') 
            
    def set_actuator_param(self, pixeltime=1000):

        self.adw.Set_FPar(46, tools.timeToADwin(pixeltime)) #qué es el 36 de focus.py
        
        # set-up actuator initial param
        
        currentXposition = tools.convert(self.adw.Get_FPar(70), 'UtoX')
        currentYposition = tools.convert(self.adw.Get_FPar(71), 'UtoX')
    
        x_f = tools.convert(currentXposition, 'XtoU')
        y_f = tools.convert(currentYposition, 'XtoU')
        
        self.adw.Set_FPar(40, x_f)
        self.adw.Set_FPar(41, y_f)
            
        self.adw.Set_Par(40, 1)
        
    def actuator_xy(self, x_f, y_f):
        
#        print(datetime.now(), '[xy_tracking] actuator x, y =', x_f, y_f)
        
        x_f = tools.convert(x_f, 'XtoU')
        y_f = tools.convert(y_f, 'XtoU')
        
        self.adw.Set_FPar(40, x_f)
        self.adw.Set_FPar(41, y_f)
        
        self.adw.Set_Par(40, 1)    
        
    def set_moveTo_param(self, x_f, y_f, z_f, n_pixels_x=128, n_pixels_y=128,
                         n_pixels_z=128, pixeltime=2000):

        x_f = tools.convert(x_f, 'XtoU')
        y_f = tools.convert(y_f, 'XtoU')
        z_f = tools.convert(z_f, 'XtoU')

        self.adw.Set_Par(21, n_pixels_x)
        self.adw.Set_Par(22, n_pixels_y)
        self.adw.Set_Par(23, n_pixels_z)

        self.adw.Set_FPar(23, x_f)
        self.adw.Set_FPar(24, y_f)
        self.adw.Set_FPar(25, z_f)

        self.adw.Set_FPar(26, tools.timeToADwin(pixeltime))

    def moveTo(self, x_f, y_f, z_f): 

        self.set_moveTo_param(x_f, y_f, z_f)
        self.adw.Start_Process(2)
            
    def reset(self):
        
        self.initial = True
        self.xData = np.zeros(self.npoints)
        self.yData = np.zeros(self.npoints)
        self.time = np.zeros(self.npoints)
        self.ptr = 0
        self.startTime = time.time()
        self.j = 0  # iterator on the data array
        
        self.changedData.emit(self.time, self.xData, self.yData)
        
    def reset_data_arrays(self):
        
        self.time_array = np.zeros(self.buffersize, dtype=np.float16)
        self.x_array = np.zeros(self.buffersize, dtype=np.float16)
        self.y_array = np.zeros(self.buffersize, dtype=np.float16)
        
        
    def export_data(self):
        
        """
        Exports the x, y and t data into a .txt file
        """

#        fname = self.filename
##        filename = tools.getUniqueName(fname)    # TO DO: make compatible with psf measurement and stand alone
#        filename = fname + '_xydata.txt'
        
        fname = self.filename
        #case distinction to prevent wrong filenaming when starting minflux or psf measurement
        if fname[0] == '!':
            filename = fname[1:]
        else:
            filename = tools.getUniqueName(fname)
        filename = filename + '_xydata.txt'
        
        size = self.j
        savedData = np.zeros((3, size))

        savedData[0, :] = self.time_array[0:self.j]
        savedData[1, :] = self.x_array[0:self.j]
        savedData[2, :] = self.y_array[0:self.j]
        
        np.savetxt(filename, savedData.T,  header='t (s), x (nm), y(nm)') # transpose for easier loading
        
        print(datetime.now(), '[xy_tracking] xy data exported to', filename)

    @pyqtSlot(bool)    
    def get_stop_signal(self, stoplive):
        
        """
        Connection: [psf] xyStopSignal
        Description: stops liveview, tracking, feedback if they where running to
        start the psf measurement with discrete xy - z corrections
        """
                
        self.toggle_feedback(False)
        self.toggle_tracking(False)
        
        self.reset()
        self.reset_data_arrays()
        
        self.save_data_state = True  # TO DO: sync this with GUI checkboxes (Lantz typedfeat?)
            
        if not stoplive:
            self.liveviewSignal.emit(False)
            
    @pyqtSlot(bool)
    def get_save_data_state(self, val):
        
        '''
        Connection: [frontend] saveDataSignal
        Description: gets value of the save_data_state variable, True -> save,
        Fals -> don't save
        
        '''
        
        self.save_data_state = val
        
        if DEBUG:
            print(datetime.now(), '[xy_tracking] save_data_state = {}'.format(val))
    
    @pyqtSlot(str, int, list) #antes se usaba roi_coordinates_array que se convertía a int en ROIcoordinates
    def get_roi_info(self, roi_type, N, coordinates_list): #Toma la informacion del ROI que viene de emit_roi_info en el frontend
        
        '''
        Connection: [frontend] roiInfoSignal
        Description: gets coordinates of the ROI in the GUI
        
        '''
        if roi_type == 'xy':
                            
            self.roi_coordinates_list = coordinates_list
        
            if DEBUG:
                print(datetime.now(), '[xy_tracking] got ROI coordinates list')
                
        if roi_type == 'z':
            
            self.zROIcoordinates = coordinates_list[0].astype(int)
            
     
    @pyqtSlot()    
    def get_lock_signal(self):
        
        '''
        Connection: [minflux] xyzStartSignal
        Description: activates tracking and feedback
        
        '''
        
        if not self.camON:
            self.liveviewSignal.emit(True)
        
        self.toggle_tracking(True)
        self.toggle_feedback(True)
        self.save_data_state = True
        
        self.updateGUIcheckboxSignal.emit(self.tracking_value, 
                                          self.feedback_active, 
                                          self.save_data_state)
        
        if DEBUG:
            print(datetime.now(), '[xy_tracking] System xy locked')

    @pyqtSlot(np.ndarray, np.ndarray) 
    def get_move_signal(self, r, r_rel):            
        
        self.toggle_feedback(False)
#        self.toggle_tracking(True)
        
        self.updateGUIcheckboxSignal.emit(self.tracking_value, 
                                          self.feedback_active, 
                                          self.save_data_state)
        
        x_f, y_f = r

        self.actuator_xy(x_f, y_f)
         
        if DEBUG:
            print(datetime.now(), '[xy_tracking] Moved to', r)
        
#        # Lock again
        
#        print(datetime.now(), '[xy_tracking] initial x and y', self.initialx, self.initialy)
#        print(datetime.now(), '[xy_tracking] dx, dy', r_rel)
##        self.initial = True # to lock at a new position, TO DO: fix relative position tracking
#        self.initialx = self.currentx - r_rel[0] * 1000 # r_rel to nm
#        self.initialy = self.currenty - r_rel[1] * 1000 # r_rel to nm
#        print(datetime.now(), '[xy_tracking] initial x and y', self.initialx, self.initialy)
        
#        self.toggle_feedback(True) # TO DO: fix each position lock
        

    def start_tracking_pattern(self):
        
        self.pattern = True
        self.initcounter = self.counter

    def make_tracking_pattern(self, step):
                
        if (step < 2) or (step > 5):
            return
        elif step == 2:
            dist = np.array([0.0, 20.0])
        elif step == 3:
            dist = np.array([20.0, 0.0])
        elif step == 4:
            dist = np.array([0.0, -20.0])
        elif step == 5:
            dist = np.array([-20.0, 0.0])
        
        
        self.initialx = self.initialx + dist[0]
        self.initialy = self.initialy + dist[1]
        self.displacement = self.displacement + dist
        
        print(datetime.now(), '[xy_tracking] Moved setpoint by', dist)
      
    @pyqtSlot(str)    
    def get_end_measurement_signal(self, fname):
        
        '''
        From: [minflux] xyzEndSignal or [psf] endSignal
        Description: at the end of the measurement exports the xy data

        '''
        
        self.filename = fname
        self.export_data()
        
        
        self.toggle_feedback(False) # TO DO: decide whether I want feedback ON/OFF at the end of measurement
        #check
        self.toggle_tracking(False)
        self.pattern = False
        
        self.reset()
        self.reset_data_arrays()
            
    def make_connection(self, frontend):
        if DEBUG:
            print("Connecting backend to frontend")
            
        frontend.roiInfoSignal.connect(self.get_roi_info)
        frontend.closeSignal.connect(self.stop)
        frontend.saveDataSignal.connect(self.get_save_data_state)
        frontend.exportDataButton.clicked.connect(self.export_data)
        frontend.clearDataButton.clicked.connect(self.reset)
        frontend.clearDataButton.clicked.connect(self.reset_data_arrays)
        frontend.trackingBeadsBox.stateChanged.connect(lambda: self.toggle_tracking(frontend.trackingBeadsBox.isChecked()))
        frontend.shutterCheckbox.stateChanged.connect(lambda: self.toggle_tracking_shutter(8, frontend.shutterCheckbox.isChecked()))
        frontend.liveviewButton.clicked.connect(self.liveview)
        print("liveviewButton connected liveview - line 1263")
        frontend.xyPatternButton.clicked.connect(lambda: self.make_tracking_pattern(1))
        frontend.feedbackLoopBox.stateChanged.connect(lambda: self.toggle_feedback(frontend.feedbackLoopBox.isChecked()))
        
        # TO DO: clean-up checkbox create continous and discrete feedback loop
        
        # lambda function and gui_###_state are used to toggle both backend
        # states and checkbox status so that they always correspond 
        # (checked <-> active, not checked <-> inactive)
        
    @pyqtSlot()    
    def stop(self): #nuevo modificación, sigo focus.py
        self.toggle_tracking_shutter(8, False)
        time.sleep(1)
        
        self.viewtimer.stop()
        
        #prevent system to throw weird errors when not being able to close the camera, see uc480.py --> close()
        self.reset()
        
        # Go back to 0 position

        x_0 = 0
        y_0 = 0
        z_0 = 0

        self.moveTo(x_0, y_0, z_0)
        
        self.camera.close()
        print(datetime.now(), '[xy_tracking] Thorlabs camera shut down')
        

if __name__ == '__main__':

    if not QtGui.QApplication.instance():
        app = QtGui.QApplication([])
    else:
        app = QtGui.QApplication.instance()
        
    #app.setStyle(QtGui.QStyleFactory.create('fusion'))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # initialize devices
    
    DEVICENUMBER = 0x1
    adw = ADwin.ADwin(DEVICENUMBER, 1)
    scan.setupDevice(adw)
    
    #if camera wasnt closed properly just keep using it without opening new one
    
    try:
        camera = uc480.UC480_Camera()
        print("Objeto camera class UC480_Camera creado")
    except:
        pass
    
    gui = Frontend()
    if DEBUG:
        print("gui class Frontend instanced, FC")
    worker = Backend(camera, adw)

    print("connection 1")
    gui.make_connection(worker)
    print("connection 2")
    worker.make_connection(gui)
    
    #Creamos un Thread y movemos el worker ahi, junto con sus timer, ahi realizamos la conexión
    
    xyThread = QtCore.QThread()
    worker.moveToThread(xyThread)
    worker.viewtimer.moveToThread(xyThread)
    worker.viewtimer.timeout.connect(worker.update)
    xyThread.start()

    # initialize fpar_70, fpar_71, fpar_72 ADwin position parameters
    
    pos_zero = tools.convert(0, 'XtoU')
        
    worker.adw.Set_FPar(70, pos_zero)
    worker.adw.Set_FPar(71, pos_zero)
    worker.adw.Set_FPar(72, pos_zero)
    
    worker.moveTo(10, 10, 10) # in µm
    
    time.sleep(0.200)
        
    gui.setWindowTitle('xyz drift correction test')
    gui.show()
    app.exec_()
        