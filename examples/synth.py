#!/usr/bin/env python

import os
import signal

import skywriter
from pdtone import PDTone


tone = PDTone()

@skywriter.move()
def move(x, y, z):
  tone.power_on()
  print(x,y,z)
  tone.custom('x', x * 1000.0) #300.0 + (x*600.0))
  tone.custom('y', y * 1000.0) #300.0 + (y*600.0))
  tone.custom('z', z * 1000.0) #(z*10.0)+1)

signal.pause()
