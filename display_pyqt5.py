# -*- coding: utf-8 -*-
"""
Created on Mon Oct 30 16:22:09 2023

@author: Minflux
"""

import math
import pyqtgraph as pg
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import QRectF, pyqtSlot

class Display(pg.GraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__scene = pg.GraphicsScene()
        self.setScene(self.__scene)

    @pyqtSlot(QImage)
    def on_image_received(self, image: QImage):
        self.__scene.set_image(image)
        self.update()
