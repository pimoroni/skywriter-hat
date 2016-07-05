#!/usr/bin/env python
import skywriter
import signal
import autopy

some_value = 0

width, height = autopy.screen.get_size()

@skywriter.move()
def move(x, y, z):
  #print( x, y, z )
  x = (x) * width
  y = (y) * height

  x = int(x)
  y = height - int(y)

  if( y > 799 ):
   y = 799

  autopy.mouse.move(x, y)
  #print( int(x), int(y) )

@skywriter.flick()
def flick(start,finish):
  print('Got a flick!', start, finish)

@skywriter.airwheel()
def spinny(delta):
  global some_value
  some_value += delta
  if some_value < 0:
  	some_value = 0
  if some_value > 10000:
    some_value = 10000
  print('Airwheel:', some_value/100)

@skywriter.double_tap()
def doubletap(position):
  print('Double tap!', position)

@skywriter.tap()
def tap(position):
  print('Tap!', position)

@skywriter.touch()
def touch(position):
  print('Touch!', position)

signal.pause()
