#Skywriter

This repository contains libraries and examples for the Skywriter boards.

##Installing Software

You can usually use our quick-n-easy installer to get Skywriter up and running on a Pi. Type the following into a terminal on your Raspberry Pi, use LXTerminal if you're looking at the desktop:

```
curl -sSL get.pimoroni.com/skywriter | bash
```

For full instructions on installing Skywriter, check out [the library README file](/python/library/README.md).

##Skywriter to Pi Connection

You can use a full-sized Skywriter board with your Raspberry Pi and our library by mimicking the connections that the HAT users. They are as follows:

Skywriter  | Raspberry Pi
-----------|--------------
GND        | GND
TRFR       | GPIO 27 
RESET      | GPIO 17
SCL        | GPIO 3 / SCL 
SDA        | GPIO 2 / SDA
VCC        | 3V
