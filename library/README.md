Skywriter
=========

Support code and API library for the Skywriter Raspberry Pi HAT and breakout board.

##Quick-Install

If you're using Skywriter on a Raspberry Pi, you can use our quick installer to get everything set up and configured for you. Just open up LXTerminal and type:

```
curl -sSL get.pimoroni.com/skywriter | bash
```

##Step-by-Step Install

###Pre-Requisites

Skywriter needs i2c enabled, you can use raspi-config to do this, or run:

```
curl -sSL get.pimoroni.com/i2c | bash
```

You'll also need to install smbus:

```
sudo apt-get install python-smbus
```

###Installation

####From pip

```
sudo apt-get install python-pip
sudo pip install skywriter
```

####From source

Clone this library, make your way into this directory:

```
git clone https://github.com/pimoroni/skywriter-hat
cd skywriter-hat/python/library
```
    
And then install the library with:

```
sudo python setup.py install
```
