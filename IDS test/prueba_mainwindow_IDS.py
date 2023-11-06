# -*- coding: utf-8 -*-
"""
Created on Thu Oct 12 14:04:41 2023

@author: Minflux
"""
import sys
import numpy as np
import time
import scipy.ndimage as ndi
import matplotlib.pyplot as plt
from datetime import date, datetime
import os

import pyqtgraph as pg #Se podría usar también Pyside6
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
import qdarkstyle # see https://stackoverflow.com/questions/48256772/dark-theme-for-in-qt-widgets

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

import sys
#sys.path.append('C:\Program Files\Thorlabs\Scientific Imaging\ThorCam') #Comento porque import sys está en mainwindow y parece ir a la ruta indicada sin problemas
#No sabía cuál ruta poner  porque veo dlls en ids_peak en program / generic_sdk /comfort_sdk
# install from https://instrumental-lib.readthedocs.io/en/stable/install.html
#from instrumental.drivers.cameras import uc480
#from instrumental import Q_
from ids_peak import ids_peak
from mainwindow import MainWindow #La clase MainWindow posee todas las funciones  open_device/cloe_device/start_acquisition/stop_acquisition
from display import Display

if __name__ == '__main__':
    
    app = QtGui.QApplication([])

    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    print(QtCore.QDateTime.currentDateTime(), '[focus] Focus lock module running in stand-alone mode')

    main_window = MainWindow()

    # El resto de tu código, como la configuración de la cámara IDS y otros elementos,
    # debe seguir siendo compatible con PyQt5 y no necesita cambios importantes.

    main_window.setWindowTitle('Focus lock')
    main_window.resize(1500, 500)

    main_window.show()
    app.exec_()