# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 15:54:41 2023

@author: Florencia Edorna
"""

import numpy as np
import matplotlib.pyplot as plt
import time
import tools_simulations as tools

from pqreader import load_ptu


filename = 'C:/Users/Minflux/Documents/GitHub/p-minflux/Picoharp test/Atto647N.ptu'
num_phton=200


dt = 50 # p-minflux cycle time [ns]
K = 4   # number of excitation beams
τ = np.arange(0, K)/K * dt # times of EBP pulses (1, K)
SBR = 9 # Signal to Background Ratio, TO DO: The number of photons from the BG depends on the time it collects from the beat.
size_nm = 400 # field of view size (nm)
step_nm = 1
size = int(size_nm/step_nm)
L = 30 # ditance between beam centers

#%% Simulate PSFs
PSFs = np.zeros((K, size, size))
extent = [-size_nm/2, size_nm/2, -size_nm/2, size_nm/2]
# EBP centers
pos_nm = tools.beams(K, L, center=True, d='donut')
for i in range(K):
    PSFs[i, :, :] = tools.psf(pos_nm[i], size_nm, step_nm, [0, 0], d='donut')


# %% Lectura TCSPC
channel = 1 # 1 = red, 0 = green
start_time = time.time()# Inicia el temporizador

data = load_ptu(filename)
dtime_channel_data = data[0] * data[3]['timestamps_unit']
micro_channel_data = data[2] * data[3]['nanotimes_unit']

# print(data[3]['timestamps_unit'])
# print(data[3]['nanotimes_unit'])

dtime_channel_data = dtime_channel_data[data[1] == channel]
micro_channel_data = micro_channel_data[data[1] == channel]
photon_count, edges = np.histogram(micro_channel_data[-num_phton:]*1e9, bins=[0, 25, 50, 75, 100])

r0_est = tools.pos_MINFLUX(photon_count, PSFs, SBR=SBR, prior=None, L=L)
r0_est_nm = tools.indexToSpace(r0_est, size_nm, step_nm)


end_time = time.time() # Detiene el temporizador
elapsed_time = end_time - start_time # Calcula el tiempo transcurrido en segundos

print(f"Tiempo de lectura del archivo PTU: {elapsed_time*1000:.2f} milisegundos")
print(f"Posición estimada: {r0_est_nm} nanometros")


#plt.hist(micro_channel_data[-num_phton:]*1e9, bins=4, color='blue', edgecolor='black')
# Añadir etiquetas y título
#plt.xlabel('T arrivo [ns]?')
#plt.ylabel('Frecuencia')
#plt.title('Histograma de los últimos 200 valores de micro_channel_data')
# Mostrar el histograma
#plt.show()
