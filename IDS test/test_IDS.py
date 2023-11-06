# -*- coding: utf-8 -*-
"""
Created on Thu Oct  5 11:28:02 2023

@author: Florencia D. Choque
"""
from pyueye import ueye
import numpy as np
import cv2

def main():
    # init camera
    hcam = ueye.HIDS(0)
    ret = ueye.is_InitCamera(hcam, None)
    print(f"initCamera returns {ret}")
    
    ret = ueye.is_CaptureVideo(hcam, ueye.IS_DONT_WAIT)
    print(f"CaptureVideo returns {ret}")
    width = 1280
    height = 1080
    bitspixel = 24
    mem_ptr = ueye.c_mem_p()

    # get data from camera and display
    lineinc = width * int((bitspixel + 7) / 8)
    while True:
        img = ueye.get_data(mem_ptr, width, height, bitspixel, lineinc, copy=True)
        img = np.reshape(img, (height, width, 3))
        cv2.imshow('uEye Python Example (q to exit)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    
    # cleanup
    ret = ueye.is_StopLiveVideo(hcam, ueye.IS_FORCE_VIDEO_STOP)
    print(f"StopLiveVideo returns {ret}")
    ret = ueye.is_ExitCamera(hcam)
    print(f"ExitCamera returns {ret}")
    
if __name__ == '__main__':
    main()

