#!/usr/bin/env python
import skywriter
import signal
from pdtone import PDTone

tone = PDTone()

@skywriter.move()
def move(x, y, z):
  tone.power_on()
  print(x,y,z)
  tone.tone(z*1500)

signal.pause()
