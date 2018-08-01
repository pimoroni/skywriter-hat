Skywriter HAT Examples
======================

By virture of the Skywriter HAT being a HAT(!), and hence using the Raspberry Pi's GPIO pins, all of these examples must be run with `sudo`, for example

    sudo ./test.py

or

    sudo python test.py


keyboard.py
-----------

Enable cursor key emulation through Skywriter gestures (swipe left/right, etc).

Designed to be run within X, `startx` first.

To run, you'll first need to:

    sudo apt-get install python-dev python-xlib libxtst-dev libpng-dev python-pip

And then you'll need to:

    sudo pip install autopy


mouse.py
--------

This example does exactly what you'd expect- gives you control over the mouse with Skywriter. It probably wont be much use out of the box, though, but it's a good proof of concept and a pointer in the right direction- make it better!

Designed to be run within X, `startx` first.

To run, you'll need to:

    sudo apt-get install python-dev python-xlib libxtst-dev libpng-dev python-pip

And:

    sudo pip install autopy==0.51


pdtone.py
---------

Used in `synth.py`.


synth.py
--------

A theremin which can be run straight from the console.

To run, you'll need to install PD:

    sudo apt-get install pd


test.py
-------

Nothing exciting, simply outputs the variety of gestures, touches and movements that the Skywriter detects when you move your finger around above it.

* *Airwheel* - wave your finger in a circular pattern above the HAT
* *Touch/Tap/Doubletap* - touch, tap or double-tap one of the edges or the center of the HAT
* *X/Y/Z* - just move your finger over the HAT
* *Gestures* - try waving your hand from one side of the HAT to the other


theremin.pd
-----------

Show off your musical prowess and melodic genius with this groundbreaking 3D theremin. 

Designed to be run within X, `startx` first.

To run, you'll need to install PD:

    sudo apt-get install pd

Run as follows:

    pd theremin.pd


umouse.py
---------

A `uinput` Skywriter mouse.

To run, you'll first need to:

    sudo apt-get install libudev-dev

And then you'll need to:

    sudo pip install python-uinput
    
And finally you'll need to run `sudo modprobe uinput` before every run, or add a new line containing just `uinput` to the end of `/etc/modules` to enable automatic boot-time loading of the `uinput` module.
