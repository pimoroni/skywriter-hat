#!/usr/bin/env python

import signal
import time
from sys import exit

try:
    import uinput
except ImportError:
    exit("This script requires the uinput module\nInstall with: sudo pip install python-uinput")

import skywriter


mouse = uinput.Device([uinput.REL_X, uinput.REL_Y, uinput.BTN_LEFT])

v_x = 0
v_y = 0
v_x = 0

@skywriter.move()
def move(x, y, z):
    global v_x, v_y

    v_z = int(z * 30.0)
  
    v_x = int((x - 0.5) * v_z)
    v_y = int((y - 0.5) * v_z)
  
    print(v_x,v_y)

while True:
    time.sleep(0.01)
    mouse.emit(uinput.REL_X, v_x)
    mouse.emit(uinput.REL_Y, -v_y)

signal.pause()
