# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 12:35:00 2023

@author: USUARIO
"""

x1Data = [[14, 17, 12, 33, 44],  
       [15, 6, 27, 8, 19], 
       [23, 2, 54, 1, 4, ]] 

#xData=[[1],[6],[4],[7]]
xData=[1, 6, 4, 7]
print(xData)
xmean= np.mean(xData, axis=None)
print("xmean",xmean, type(xmean))
print("size xData", np.size(xData))
print("std sqrt", np.sqrt(xmean))
xstd_value=np.std(xData)
print(xstd_value)