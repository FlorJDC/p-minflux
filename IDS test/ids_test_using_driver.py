# -*- coding: utf-8 -*-
"""
Created on Tue Nov  7 11:47:18 2023

@author: Minflux
"""


import drivers.ids_cam as ids_cam


class Backend:
    def __init__(self, device,*args, **kwargs):
        self.cam = device #Mi nueva clase recibe mi objeto
    
        self.cam.open_device()

if __name__ == '__main__':
    device = ids_cam.IDS_U3() #Tengo mi objeto de clase IDS_U3
    worker = Backend(device) #Defino un nuevo objeto que hará algo con el objeto que le mandé