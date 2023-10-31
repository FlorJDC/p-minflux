# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 11:42:22 2023

@author: Cibion
"""
from PyQt5.QtWidgets import QWidget, QApplication, QGridLayout
#from PyQt5.QtWidgets con esto se accede a todos los metodos y clases de los widgets que voy a utilizar
#QWidget con esto se crea la ventana
#QApplication con esto se inicia la aplicacion
#QGridLayout se usa para distribuir las graficas
import pyqtgraph as pg
import sys

import numpy as np

#Creo una clase que hereda de QWidget
class GUI(QWidget): # también se podría utilizar QMyWindow o QDialog que crean ventanas
    def __init__(self): # Se crea el constructor
    #Ahora quiero heredar las clases y métodos de QWidget
        super().__init__()
        self.setWindowTitle("Grafica")
        self.setStyleSheet('background-color: #00AAAA;') #configurar el color del fondo
        self.resize(650,650) #Tamaño de la ventana
        
        self.box = QGridLayout()
        self.box.setSpacing(5)
        self.box.setContentsMargins(5,5,5,5)
        #Ahora quiero colocar el gridLayout en la ventana principal
        self.setLayout(self.box)
        
        self.graph_one()
        self.graph_two()
        
    #Creo un metodo para cada grafica
    def graph_one(self):
        x = np.arange(0,10)
        y = np.random.randint(1,10,size=10)
        bars= pg.BarGraphItem(x=x, height=y,width=0.5,brush="#00AAAA")
        plt=pg.plot()
        plt.addItem(bars)
        plt.setLabels(left= 'Y', bottom = 'X')
        plt.setTitle(title="Grafica lineal")
        self.box.addWidget(plt,0,0)
    def graph_two(self):
        plt=pg.PlotWidget(title="GRafica lineal")
        x =np.linspace(0,100,50) #o, t,t1,t2,t3,s,p,h,+,d,x
        plt.plot(x,2*np.cos(x), Symbol = 'star', symbolBrush = "#00AAAA", pen="#00AAAA", width=2, SymbolPen="#00AAAA")
        self.box.addWidget(plt,0,1)
        
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv) #sys.argv es una lista que sirve para ejecutar el programa, también puede ser una lista vacía
    my_app = GUI() 
    my_app.show()
    sys.exit(app.exec_())
    

