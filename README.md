#Skywriter

This repository contains libraries and examples for the Skywriter boards.

##Installing Software

We've created a super-easy installation script that will install all pre-requisites and get your HAT up and running in a jiffy. To run it fire up Terminal which you'll find in Menu -> Accessories -> Terminal on your Raspberry Pi desktop like so:

![Finding the terminal](terminal.jpg)

In the new terminal window type the following and follow the instructions:

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
