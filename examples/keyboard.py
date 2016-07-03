#!/usr/bin/env python
import skywriter
import signal
import autopy

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
