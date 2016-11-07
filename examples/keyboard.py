#!/usr/bin/env python

import signal
from sys import exit

try:
    import autopy
except ImportError:
    exit("This script requires the autopy module\nInstall with: sudo pip install autopy")

import skywriter


some_value = 0

@skywriter.flick()
def flick(start,finish):
  print('Got a flick!', start, finish)
  if start == "east":
    autopy.key.tap(autopy.key.K_LEFT)
  if start == "west":
    autopy.key.tap(autopy.key.K_RIGHT)
  if start == "north":
    autopy.key.tap(autopy.key.K_DOWN)
  if start == "south":
    autopy.key.tap(autopy.key.K_UP)

@skywriter.tap()
def tap(position):
  autopy.key.tap(autopy.key.K_RETURN)


signal.pause()
