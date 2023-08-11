# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 15:45:02 2023

@author: Cibion
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton

class Backend:
    def __init__(self):
        self.new_pos = {}  # Diccionario para almacenar las nuevas posiciones

    def set_new_position(self, device, channel, position):
        self.new_pos[(device, channel)] = position

    def get_new_position(self, device, channel):
        return self.new_pos.get((device, channel), 0)

class ChannelControlWidget(QWidget):
    def __init__(self, backend, device_name, channel, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.device_name = device_name
        self.channel = channel

        self.layout = QVBoxLayout()

        self.label = QLabel(f"{self.device_name} - Channel {self.channel}")
        self.value_spinbox = QSpinBox()
        self.value_spinbox.setRange(0, 100)
        self.increase_button = QPushButton("▲")
        self.decrease_button = QPushButton("▼")

        self.increase_button.clicked.connect(self.increase_value)
        self.decrease_button.clicked.connect(self.decrease_value)

        value_layout = QHBoxLayout()
        value_layout.addWidget(self.decrease_button)
        value_layout.addWidget(self.value_spinbox)
        value_layout.addWidget(self.increase_button)

        self.layout.addWidget(self.label)
        self.layout.addLayout(value_layout)

        self.setLayout(self.layout)

    def increase_value(self):
        current_value = self.value_spinbox.value()
        self.value_spinbox.setValue(current_value + 1)
        self.backend.set_new_position(self.device_name, self.channel, current_value + 1)

    def decrease_value(self):
        current_value = self.value_spinbox.value()
        self.value_spinbox.setValue(current_value - 1)
        self.backend.set_new_position(self.device_name, self.channel, current_value - 1)

class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()

        self.channel_widgets = []

        device_names = ["Device 1", "Device 2"]
        num_channels = 4

        for device_name in device_names:
            for channel in range(1, num_channels + 1):
                channel_widget = ChannelControlWidget(backend, device_name, channel)
                self.channel_widgets.append(channel_widget)
                self.layout.addWidget(channel_widget)

        self.central_widget.setLayout(self.layout)

def main():
    app = QApplication(sys.argv)
    backend = Backend()
    window = MainWindow(backend)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()