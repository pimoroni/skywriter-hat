Skywriter Arduino Library
=========================

### Installation
Place the Skywriter library folder into Arduino/libraries folder.

### Usage
Skywriter is instantiated for you, just include the header file:

    #include <skywriter.h>

And you'll have a "Skywriter" object ready to go.

Fire it up in your setup function like so:

    void setup(){
      Skywriter.begin(PIN_TRFD, PIN_RESET)
    }

To check for a new data packet, you must "poll" Skywriter in your main loop, like so:

    void loop(){
      Skywriter.poll()
    }

To handle an incoming XYZ update, gesture, airwheel or touch you should create a handler function. This example shows XYZ coordinates being output to Serial:

    #include <Wire.h>
    #include <skywriter.h>

    void setup() {
      Serial.begin(9600);
      while(!Serial){};
      Serial.println("Hello World!");

      Skywriter.begin(PIN_TRFD, PIN_REST);
      Skywriter.onXYZ(handle_xyz);
    }

    void loop() {
      Skywriter.poll();
    }

    void handle_xyz(unsigned int x, unsigned int y, unsigned int z){
     char buf[17];
     sprintf(buf, "%05u:%05u:%05u", x, y, z);
     Serial.println(buf);
    }
