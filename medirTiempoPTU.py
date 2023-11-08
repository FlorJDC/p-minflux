import numpy as np
import PicoHarp.Read_PTU as Read_PTU
import time

# Ruta del archivo PTU
file_path = 'C:/Users/Minflux/Documents/GitHub/p-minflux/Atto647N.ptu'

# Inicia el temporizador
start_time = time.time()

# Lee el archivo PTU
with open(file_path, 'rb') as inputfile:
    numRecords = 200  # Especifica el número de registros
    relTime, absTime = Read_PTU.readPT3(inputfile, numRecords)

# Detén el temporizador
end_time = time.time()

# Calcula el tiempo transcurrido en segundos
elapsed_time = end_time - start_time


# Realizar las mismas operaciones que en el código original
globRes = 5e-8  # en segundos, corresponde a sync @20 MHz
timeRes = 8 * 1e-12  # Resolución de tiempo en segundos (8 ps)

# Convierte los datos al formato deseado
relTime_ns = relTime * timeRes * 1e9  # en nanosegundos
absTime_ns = absTime * globRes * 1e9  # en nanosegundos

# Ahora puedes realizar las mismas operaciones que en el código original con relTime_ns y absTime_ns
# Por ejemplo, calcular un histograma de relTime_ns o absTime_ns y graficarlo.


print(f"Tiempo de lectura del archivo PTU: {elapsed_time*1000:.2f} milisegundos")
