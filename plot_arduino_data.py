# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 19:30:09 2017
@author: rlc
"""
import sys
import ctypes
import time
import pyqtgraph as pg
import threading
import serial
from collections import deque
from PyQt4.QtCore import *
from PyQt4.QtGui import *
__version__ = '1.0'
class MainWindow(QMainWindow):
    newdata = pyqtSignal(object)
    def __init__(self, filename=None, parent=None):
        super(MainWindow, self).__init__(parent)
        length = 100
        self.disbuffer = deque([1.]*length, length)
        self.timebuffer =  deque([0.]*length, length)
        self.connected = False
        self.port = 'COM4'
        self.baud = 115200
             
        QTimer.singleShot(0, self.startThread)
        self.cwidget = QWidget()
        vb = QVBoxLayout()
    
        p = pg.PlotWidget()
        vb.addWidget(p)
        self.cwidget.setLayout(vb)
        self.setCentralWidget(self.cwidget)
        self.curve = p.plot(pen=(200,200,200), symbolBrush=(255,0,0), symbolPen='w')
        
        self.curve.setData(self.disbuffer, self.disbuffer)
        self.newdata.connect(self.onNewData)

    def onNewData(self, signal):
        if self.timebuffer[0] != 0:
            self.curve.setData(self.timebuffer, signal)
        else:
            self.curve.setData(signal)

    def startThread(self):
        print 'Start lisnening to the COM-port'
        serial_port = serial.Serial(self.port, self.baud, timeout=0)
        thread = threading.Thread(target=self.read_from_port, args=(serial_port,))
        thread.setDaemon(True) #Makes sures that the threas stops when exitting the program
        thread.start()
        self.tstart = time.clock()
        
    def stopThread(self):
        print 'Stop the thread...'
        
    def handle_data(self,data):
        try:
            data = float(data)          
        except ValueError:
            data = 0.
            
        self.disbuffer.append(data)
        t = time.clock()
        dt = t-self.tstart
        self.timebuffer.append(dt)
        signal = self.disbuffer
        self.newdata.emit(signal)

    def read_from_port(self,ser):
        while True:
           bytesToRead = ser.inWaiting()
           reading = ser.read(bytesToRead).decode()
           if len(reading) > 1:
               self.handle_data(reading)

    def closeEvent(self, event):
        if self.okToContinue():
             event.accept()
             self.stopThread()
        else:
            event.ignore()

    def okToContinue(self):
        return True

if __name__ == '__main__':
    myappid = 'rlc.arduino.subproduct.version'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    form = MainWindow()

    form.show()
    app.exec_()