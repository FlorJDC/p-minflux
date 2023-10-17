# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 13:37:21 2023

@author: Nanofisica8
"""
import sys
from ids_peak import ids_peak as peak

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
            else:
                print("Device found")
         
            self.m_device = self.device_manager.Devices()[0].OpenDevice(peak.DeviceAccessType_Control)
            self.m_node_map_remote_device = self.m_device.RemoteDevice().NodeMaps()[0]
            
            if self.m_device is None:
                print("Failed to open the device")
                return False
        except Exception as e:
            str_error = str(e)
            print("error opening cam: ", str(e))

        
        return True
     
     
    def prepare_acquisition(self):
        global m_dataStream
        try:
            data_streams = self.m_device.DataStreams()
            if data_streams.empty():
              print("no data streams available")
              return False
            self.m_dataStream = self.m_device.DataStreams()[0].OpenDataStream()
     
            return True
        except Exception as e:
            str_error = str(e)
            print("error preparing acquisition", str(e))
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
            print("Error setting roi: ", str(e))
            return False
     
     
    def alloc_and_announce_buffers(self):
        try:
            if self.m_dataStream:
                # Flush queue and prepare all buffers for revoking
                self.m_dataStream.Flush(peak.DataStreamFlushMode_DiscardAll)
     
                # Clear all old buffers
                for buffer in self.m_dataStream.AnnouncedBuffers():
                    self.m_dataStream.RevokeBuffer(buffer)
     
                payload_size = self.m_node_map_remote_device.FindNode("PayloadSize").Value()
                print(payload_size, "-> Payload_size")
     
                # Get number of minimum required buffers
                num_buffers_min_required = self.m_dataStream.NumBuffersAnnouncedMinRequired()
                
                print("num_buffers_min_required: ", num_buffers_min_required)
     
                # Alloc buffers
                for i in range(num_buffers_min_required+1):
                    buffer = self.m_dataStream.AllocAndAnnounceBuffer(payload_size)
                    print("type buffer",type(buffer))
                    self.m_dataStream.QueueBuffer(buffer)
                return True
        except Exception as e:
            str_error = str(e)
            print("Error in buffers: ", str(e))
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
     
     
    def work(self):     
        if not self.open_camera():
            # error
            sys.exit(-1)
        if not self.prepare_acquisition():
            # error
            sys.exit(-2)
        if not self.set_roi(16, 16, 256, 256): #Antes en lugar 256 estaba 128
            # error
            sys.exit(-3)
        if not self.alloc_and_announce_buffers():
            # error
            sys.exit(-4)
        if not self.start_acquisition():
            # error
            sys.exit(-5)
        
        peak.Library.Close()
        sys.exit(0)

     
     
if __name__ == '__main__':
    device = ids_cam()
    device.work()

    

