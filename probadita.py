# -*- coding: utf-8 -*-
"""
Created on Mon May 22 17:49:28 2023

@author: USUARIO
"""

from PyQt5.QtCore import * 
from PyQt5.QtGui import * 
from PyQt5.QtWidgets import * 
import sys
  
  
class Window(QMainWindow):
    def __init__(self):
        super().__init__()
  
  
        # set the title
        self.setWindowTitle("Python")
  
        width = 300
        height = 200
  
        # setting the minimum size
        self.setMinimumSize(width, height)
          
        # creating a label widget
        self.label_1 = QLabel("Minimum size", self)
  
        # moving position
        self.label_1.move(0, 0)
  
        # setting up the border
        self.label_1.setStyleSheet("border :3px solid black;")
  
        # resizing label
        self.label_1.resize(120, 80)
  
        # show all the widgets
        self.show()
  
  
# create pyqt5 app
App = QApplication(sys.argv)
  
# create the instance of our Window
window = Window()
  
# start the app
sys.exit(App.exec())