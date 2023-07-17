#!/usr/bin/env python
# coding: utf-8

from drivers import minilasevo
import time

#%%
laser = minilasevo.MiniLasEvo('COM5')
#%%

print('idn:', laser.idn())
print('software version:', laser.software_version())
print('emission wavelength:', laser.emission_wavelength())
print('operating hours:', laser.operating_hours())
print('available features:', laser.available_features())


# TURNS ON THE LASER
laser.enabled = True
laser.power = 5

time.sleep(10)

laser.power = 0
laser.enabled = False

#TURNS ON THE LASER TWICE
laser.enabled = True
laser.power = 10

time.sleep(10)

laser.power = 0
laser.enabled = False

# AQUÌ SE TOMA UN TIEMPO

laser.enabled = True
laser.power = 10

time.sleep(10)

laser.power = 0
laser.enabled = False
