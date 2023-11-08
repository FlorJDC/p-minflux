# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 15:54:41 2023

@author: Florencia Edorna
"""


import numpy as np
import matplotlib.pyplot as plt

from pqreader import load_ptu


TCSPC_filename = 'Atto647N.ptu'


#%% Lectura TCSPC 
#Functions

def read_ptu(filename, channel):
    data = load_ptu(filename)
    dtime_channel_data = data[0]*data[3]['timestamps_unit']
    micro_channel_data = data[2]*data[3]['nanotimes_unit'] 
    
    print(data[3]['timestamps_unit'])
    print(data[3]['nanotimes_unit'])
    
    

    dtime_channel_data = dtime_channel_data[data[1]==channel]
    micro_channel_data = micro_channel_data[data[1]==channel]

    return micro_channel_data,dtime_channel_data, data[3]['nanotimes_unit'] 

def obtain_histogram_values(x, bins): # obtain bins and values from histogram
    histogram = np.histogram(x, bins)
    values_histogram = histogram[0]
    bins_histogram = histogram[1][:-1]+0.5*(histogram[1][1]-histogram[1][0])
    return bins_histogram, values_histogram

       
#%% Read PTU

channel = 1 # 1 = red, 0 = green
micro_channel_data,dtime_channel_data, nanotime_resol =  read_ptu(TCSPC_filename, channel)




#%% Plot time trace and decay

bin_macrotime = 0.001 # Time trace bin, seconds
bin_microtime = nanotime_resol
max_macrotime = np.max(dtime_channel_data)
max_microtime = np.max(micro_channel_data)

macrotime = np.arange(start = 0, stop = max_macrotime, step =  bin_macrotime) # Tiempo total de adquisiscion.  
microtime = np.arange(start = 0, stop = max_microtime, step =  bin_microtime)

bins_macrotime, values_macrotime = obtain_histogram_values(dtime_channel_data, macrotime)
bins_microtime, values_microtime = obtain_histogram_values(micro_channel_data, microtime)


fig, ax = plt.subplots()
ax.plot(bins_macrotime, values_macrotime)
ax.set_title('Adquisición tiempo macro')
ax.set(xlabel='t (s)', ylabel='Intensity')

fig, ax = plt.subplots()
ax.plot(bins_microtime, values_microtime)
ax.set_title('Excitación tiempo micro')
ax.set(xlabel='t', ylabel='Intensity')
ax.set_yscale('log')
