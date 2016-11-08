#!/usr/bin/env python

import signal
from sys import exit

try:
    import autopy
except ImportError:
    exit("This script requires the autopy module\nInstall with: sudo pip install autopy")

import skywriter


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
