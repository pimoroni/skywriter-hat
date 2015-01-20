Skywriter
=========

Support code and API library for the Skywriter Raspberry Pi HAT and breakout board.

Pre-Requisites
==============

Skywriter needs i2c enabled, you can use raspi-config to do this, or run:

    curl -sSL get.pimoroni.com/i2c | bash

Installation
============

From pip
--------

    sudo apt-get install python-pip
    sudo pip install skywriter

From source
-----------

Clone this library, make your way into this directory:

    git clone https://github.com/pimoroni/skywriter-hat
    cd skywriter-hat/python/library
    
And then install the library with:

    sudo python setup.py install
