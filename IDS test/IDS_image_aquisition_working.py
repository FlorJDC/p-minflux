# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 13:37:21 2023

@author: Florencia D. Choque 
Script for taking pictures using IDS Industrial Camera U3-3060CP-M-GL Rev.2.2
Win 10 - 64 bit
Full cheap 1920x1200 
It's better to revoke buffers in a separate function as it is done here.
The sensor gives us a bayered image that can be debayered using ids_peak_ipl
The converted image can then be processed to convert raw data to image
The faster process: taking just 1 channel
User Manual: https://de.ids-imaging.com/manuals/ids-peak/ids-peak-user-manual/1.3.0/en/basics-bayer-pattern.html
"""
import sys
from ids_peak import ids_peak as peak
from ids_peak_ipl import ids_peak_ipl 
import matplotlib.pyplot as plt
from ids_peak import ids_peak_ipl_extension
import numpy as np
import time


class ids_cam:
    def __init__(self):
        
        self.device_manager = None
        self.m_dataStream = None
        self.m_node_map_remote_device = None
        self.m_device=None
        peak.Library.Initialize() 
 
    def open_camera(self):
      
        try:
            
            self.device_manager = peak.DeviceManager.Instance()         

            self.device_manager.Update()

            if self.device_manager.Devices().empty():
                print("No device found")
                return False
            else:
                print("Device found")
         
            self.m_device = self.device_manager.Devices()[0].OpenDevice(peak.DeviceAccessType_Control)
            self.m_node_map_remote_device = self.m_device.RemoteDevice().NodeMaps()[0]
            
            if self.m_device is None:
                print("Failed to open the device")
                return False
            
            return True
        
        except Exception as e:
            str_error = str(e)
            print("error opening cam: ", str_error)
            return False

    def prepare_acquisition(self):
        global m_dataStream
        try:
            data_streams = self.m_device.DataStreams()
            if data_streams.empty():
              print("no data streams available")
              return False
            self.m_dataStream = self.m_device.DataStreams()[0].OpenDataStream()
            print(type(self.m_dataStream))
     
            return True
        except Exception as e:
            str_error = str(e)
            print("error preparing acquisition", str_error)
            return False  
     
    def set_roi(self,x, y, width, height):
        try:
            # Get the minimum ROI and set it. After that there are no size restrictions anymore
            x_min = self.m_node_map_remote_device.FindNode("OffsetX").Minimum()
            print("x_min:", x_min)
            y_min = self.m_node_map_remote_device.FindNode("OffsetY").Minimum()
            print("y_min:", y_min)
            w_min = self.m_node_map_remote_device.FindNode("Width").Minimum()
            print("w_min:", w_min)
            h_min = self.m_node_map_remote_device.FindNode("Height").Minimum()
            print("h_min:", h_min)
     
            self.m_node_map_remote_device.FindNode("OffsetX").SetValue(x_min)
            self.m_node_map_remote_device.FindNode("OffsetY").SetValue(y_min)
            self.m_node_map_remote_device.FindNode("Width").SetValue(w_min)
            self.m_node_map_remote_device.FindNode("Height").SetValue(h_min)
     
            # Get the maximum ROI values
            x_max = self.m_node_map_remote_device.FindNode("OffsetX").Maximum()
            print("x_max:", x_max)
            y_max = self.m_node_map_remote_device.FindNode("OffsetY").Maximum()
            print("y_max:", y_max)
            w_max = self.m_node_map_remote_device.FindNode("Width").Maximum()
            print("w_max:", w_max)
            h_max = self.m_node_map_remote_device.FindNode("Height").Maximum()
            print("h_max:", h_max)
     
            if (x < x_min) or (y < y_min) or (x > x_max) or (y > y_max):
                return False
            elif (width < w_min) or (height < h_min) or ((x + width) > w_max) or ((y + height) > h_max):
                print("Here")
                return False
            else:
                # Now, set final AOI
                self.m_node_map_remote_device.FindNode("OffsetX").SetValue(x)
                self.m_node_map_remote_device.FindNode("OffsetY").SetValue(y)
                self.m_node_map_remote_device.FindNode("Width").SetValue(width)
                self.m_node_map_remote_device.FindNode("Height").SetValue(height)
                return True
        except Exception as e:
            str_error = str(e)
            print("Error setting roi: ", str_error)
            return False
         
    def alloc_and_announce_buffers(self):
        try:
            if self.m_dataStream:
                self.revoke_buffers()
                payload_size = self.m_node_map_remote_device.FindNode("PayloadSize").Value()
                print(payload_size, "-> Payload_size") # Payload_size in this case is: 65536 bytes, for width = 256 and height = 256
     
                # Get number of minimum required buffers
                num_buffers_min_required = self.m_dataStream.NumBuffersAnnouncedMinRequired()
                print("num_buffers_min_required: ", num_buffers_min_required)
     
                # Alloc buffers
                for i in range(num_buffers_min_required):
                    try:
                        buffer = self.m_dataStream.AllocAndAnnounceBuffer(payload_size)
                        self.m_dataStream.QueueBuffer(buffer)
                    except Exception as e:
                        str_error = str(e)
                        print("Error en parte nueva de buffers: ", str_error)
                return True
        except Exception as e:
            str_error = str(e)
            print("Error in buffers: ", str_error)
            return False
                
    def revoke_buffers(self):
        try:
            if self.m_dataStream:
                # Flush queue and prepare all buffers for revoking
                self.m_dataStream.Flush(peak.DataStreamFlushMode_DiscardAll)
     
                # Clear all old buffers
                for buffer in self.m_dataStream.AnnouncedBuffers():
                    self.m_dataStream.RevokeBuffer(buffer)
                return True
        except Exception as e:
            str_error = str(e)
            print("Error revoking buffers: ", str_error)
            return False     
     
    def start_acquisition(self):
        try:
            print("Line 0 in starting acquisition")
            #print("peak.core.AcquisitionStartMode.Default: ", peak.AcquisitionStartMode_Default, " . peak.core.DataStream.INFINITE_NUMBER", peak.DataStream.INFINITE_NUMBER)
            self.m_dataStream.StartAcquisition()
            print("Line 1 in starting acquisition")
            self.m_node_map_remote_device.FindNode("TLParamsLocked").SetValue(1)
            print("Line 2 in starting acquisition")
            self.m_node_map_remote_device.FindNode("AcquisitionStart").Execute()
            print("Line 3 in starting acquisition")
            return True
        
        except Exception as e:
            str_error = str(e)
            print("Error starting acquisition",str_error)
            return False
    
    def show_image(self):
        try:
            # Get buffer from device's DataStream. Wait 5000 ms. The buffer is automatically locked until it is queued again.
            if self.m_dataStream:
                print("Estoy en show_image: ",type(self.m_dataStream))
                # Get buffer from device's datastream
                buffer = self.m_dataStream.WaitForFinishedBuffer(5000)
                print(type(buffer))
                print("buffer pixel format",buffer.PixelFormat())
                print("buffer basePtr", buffer.BasePtr())
                print("buffer size: ", buffer.Size(), "buffer width: ", buffer.Width(), "buffer height: ", buffer.Height())
                #image = ids_peak_ipl.Image.CreateFromSizeAndBuffer(buffer.PixelFormat(), buffer.BasePtr(), buffer.Size(), buffer.Width(),buffer.Height())
                ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
                print("line 180 CreateFromSizeAndPythonBuffer")
                converted_ipl_image = ipl_image.ConvertTo(ids_peak_ipl.PixelFormatName_BGRa8, ids_peak_ipl.ConversionMode_Fast)
                print("converted_ipl_image type: ", type(converted_ipl_image))
                # Queue buffer again
                self.m_dataStream.QueueBuffer(buffer)
                
                # Get raw image data from converted image and construct a 3D array
                start = time.perf_counter()
                image_np_array = converted_ipl_image.get_numpy_3D() 
                # 2D array, each element is the sum of the R,G,B,A channels
                image_sum=image_np_array[:, :, 0]
                #image_sum = np.sum(image_np_array, axis=2)
                end = time.perf_counter()
                print("Time: ", end - start) #Time:  0.0040275999999721535

                #Another way to do this is using the 1D array that contains the sequence RGBA (A: alpha channel for transparency) for each pixel: RGBARGBARGBA
                # image_np_array = converted_ipl_image.get_numpy_1D() 
                # image_sum = image_np_array.reshape(converted_ipl_image.Height(), converted_ipl_image.Width(), 4).sum(axis=2) #Time:  0.004062099999998736
                
                #If I only want a channel (R, for example), this is faster than working with the sum
                #image_red = image_np_array.reshape(converted_ipl_image.Height(), converted_ipl_image.Width(), 4)[:, :, 0] #Time:  4.239999999988697e-05
                
                print("Type image_sum: ", type(image_sum))

                #plt.imshow(image_sum)

                print("again in queue")
                return image_sum
        
        except Exception as e:
            str_error = str(e)
            print("Error showing image: ",str_error)
            #return False
     
    def work(self):     
        if not self.open_camera():
            # error
            sys.exit(-1)
        if not self.prepare_acquisition():
            # error
            sys.exit(-2)
        if not self.set_roi(16, 16, 1920, 1200): # full chip (width:1920, height: 1200)
            # error
            sys.exit(-3)
        if not self.alloc_and_announce_buffers():
            # error
            sys.exit(-4)
        if not self.start_acquisition():
            # error
            sys.exit(-5)
        image= self.show_image()

        
        print("succes getting image")
        
        peak.Library.Close()
        #sys.exit(0)
        return image
     
if __name__ == '__main__':
    device = ids_cam()
    image=device.work()
    print(type(image), image.shape)
    plt.imshow(image)
    

    

