# \file    main.py
# \author  IDS Imaging Development Systems GmbH
# \date    2021-01-15
# \since   1.2.0
# 
# \brief   This application demonstrates how to use the IDS peak API
#          combined with a QT widgets GUI to display images from Genicam
#          compatible device.
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

from mainwindow import MainWindow #La clase MainWindow posee todas las funciones  open_device/cloe_device/start_acquisition/stop_acquisition
from display import Display

print("Starting application")
app = QtGui.QApplication([])
print("Success loading app")
    # app.setStyle(QtGui.QStyleFactory.create('fusion'))
app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

print(datetime.now(), 'running mode')

main_window = MainWindow()


try:
    cam = main_window.__open_device()
    if cam:
        main_window.__display = Display()
        main_window.__layout.addWidget(main_window.__display)
        if not main_window.__start_acquisition():
            QtGui.QMessageBox.critical(main_window, "Unable to start acquisition!", QtGui.QMessageBox.Ok)
        else:
            QtGui.QMessageBox.critical(main_window, "Error with cam", "Error with cam", QtGui.QMessageBox.Ok)
except Exception as e:
    QtGui.QMessageBox.critical(main_window, "Exception", str(e), QtGui.QMessageBox.Ok)


main_window.setWindowTitle('Focus lock')
main_window.resize(1500, 500)

main_window.show()
app.exec_()
    
    
