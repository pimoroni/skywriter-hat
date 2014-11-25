#include <Wire.h>

#define SW_ADDR 0x42

#define SW_HEADER_SIZE   4

#define SW_DATA_DSP      1 //0b0000000000000001
#define SW_DATA_GESTURE  1 << 1 //0b0000000000000010
#define SW_DATA_TOUCH    1 << 2 //0b0000000000000100
#define SW_DATA_AIRWHEEL 1 << 3 //0b0000000000001000
#define SW_DATA_XYZ      1 << 4 //0b0000000000010000

#define SW_SYSTEM_STATUS 0x15
#define SW_REQUEST_MSG   0x06
#define SW_FW_VERSION    0x83
#define SW_SET_RUNTIME   0xA2
#define SW_SENSOR_DATA   0x91

#define SW_PAYLOAD_HDR_CONFIGMASK  0 // 2 Bytes
#define SW_PAYLOAD_HDR_TS          2 // 1 Byte
#define SW_PAYLOAD_HDR_SYSINFO     3 // 1 Byte
#define SW_PAYLOAD_DSP_STATUS      4
#define SW_PAYLOAD_GESTURE         6  // 4 Bytes
#define SW_PAYLOAD_TOUCH           10 // 4 Bytes
#define SW_PAYLOAD_AIRWHEEL        14 // 2 Bytes
#define SW_PAYLOAD_X               16 // 2 bytes
#define SW_PAYLOAD_Y               18 // 2 bytes
#define SW_PAYLOAD_Z               20 // 2 bytes

#define SW_SYS_POSITION            1
#define SW_SYS_AIRWHEEL            1 << 1

class SkyWriter 
{
  public:
    void begin(unsigned char pin_xfer, unsigned char pin_reset);
    void poll();
    void onTouch( void (*)(uint8_t) );
    void onAirwheel( void (*)(int) );
    void onGesture( void (*)(uint8_t) );
    void onXYZ( void (*)(uint8_t, uint8_t, uint8_t) );
  private:
    void (*handle_touch)(uint8_t)   = NULL;
    void (*handle_airwheel)(int)    = NULL;
    void (*handle_gesture)(uint8_t) = NULL;
    void (*handle_xyz)(uint8_t, uint8_t, uint8_t);
    long x, y, z, rotation, lastrotation, gesture, xfer, rst, addr;
    unsigned char command_buffer[256];
    void handle_sensor_data(unsigned char* data);
};

void SkyWriter::begin(unsigned char pin_xfer, unsigned char pin_reset){
  this->xfer = pin_xfer;
  this->rst  = pin_reset;
  this->addr = SW_ADDR;
  
  Wire.begin();
  
  pinMode(this->xfer, INPUT);
  pinMode(this->rst,  OUTPUT);
  digitalWrite(this->rst, LOW);
  pinMode(this->rst, INPUT);
  delay(50);
}

void SkyWriter::poll(){
  if (!digitalRead(this->xfer)){
    pinMode(this->xfer, OUTPUT);
    digitalWrite(this->xfer, LOW);
    
    Wire.requestFrom(this->addr, 32);
    
    unsigned char d_size,d_flags,d_seq,d_ident;
    
    if( Wire.available() >= 4 ){
      d_size  = Wire.read();
      d_flags = Wire.read();
      d_seq   = Wire.read();
      d_ident = Wire.read();
    }
    else{
      return;
    }
    
    this->command_buffer[0] = '\0';
    
    unsigned char i = 0;
    while(Wire.available()){
      this->command_buffer[i] = Wire.read();
      i++;
    }
    this->command_buffer[i] = '\0';
      
    //Serial.print("Got:");
    //Serial.print(i,DEC);
    //Serial.print(" bytes\n");
    
  
    switch(d_ident){
      case 0x91:
        //Serial.println("Got sensor data");
        this->handle_sensor_data(this->command_buffer);
        break;
      case 0x15:
        //Serial.println("Got status info");
        break;
      case 0x83:
        //Serial.println("Got fw data");
        Serial.println((const char*)this->command_buffer);
        break;
    }
    
    
    digitalWrite(this->xfer, HIGH);
    pinMode(this->xfer, INPUT);
  }
}

void SkyWriter::onTouch(    void (*function)(uint8_t) ){this->handle_touch    = function;}
void SkyWriter::onAirwheel( void (*function)(int)     ){this->handle_airwheel = function;}
void SkyWriter::onGesture(  void (*function)(uint8_t) ){this->handle_gesture  = function;}
void SkyWriter::onXYZ(      void (*function)(uint8_t,uint8_t,uint8_t) ){this->handle_xyz  = function;}

void SkyWriter::handle_sensor_data(unsigned char* data){
/*
  | HEADER | PAYLOAD
  |        |  DataOutputConfigMask 2 | TimeStamp 1 | SystemInfo 1 | Content |
  
  DataOutputConfigMask
  Bit 0 - DSPStatus
  Bit 1 - GestureInfo
  Bit 2 - TouchInfo
  Bit 3 - AirWheelInfo
  Bit 4 - XYZ Position
  Bit 5 - NoisePower
  Bit 6-7 - Reserved
  Bit 8-10 - ElectrodeConfiguration
  Bit 11 - CICData
  Bit 12 - SDData
  Bit 13-15 - Reserved
  
  SystemInfo
  Bit 0 - PositionValid, indicates xyz pos data is valid
  Bit 1 - AirWheelValid, indicates AirWheel is active and AirWheelInfo is vaid
  Bit 2 - RawDataValid, indicates CICData and SDData fields are valid
  Bit 3 - NoisePowerValid, indicates NoisePower field is valid
  Bit 4 - EnvironmentalNoise, indicates that environmental noise has been detected
  Bit 5 - Clipping, indicates that the ADCs are clipping
  Bit 6 - Reserved
  Bit 7 - DSPRunning, indicates the system is currently running
  DSPStatus - 2 bytes -
  GestureInfo - 4 bytes
  TouchInfo - 4 bytes
  AirWheelInfo - 2 bytes - first byte indicates rotation, ++ = clockwise, 32 = 1 rotation
  xyzPosition - 6 bytes - 1+2 = x, 3-4 = y, 5-6 = z
  NoisePower
  CICData
  SDData
*/  
      
      if( data[SW_PAYLOAD_HDR_CONFIGMASK] & SW_DATA_XYZ && data[SW_PAYLOAD_HDR_SYSINFO] & SW_SYS_POSITION ){
        //Serial.println("Handling xzy...");
        // Valid XYZ position
        float x = (data[SW_PAYLOAD_X+1] << 8 | data[SW_PAYLOAD_X]) / 65536.0;
        float y = (data[SW_PAYLOAD_Y+1] << 8 | data[SW_PAYLOAD_Y]) / 65536.0;
        float z = (data[SW_PAYLOAD_Z+1] << 8 | data[SW_PAYLOAD_Z]) / 65536.0;
        
        /*Serial.print(x);
        Serial.print(':');
        Serial.print(y);
        Serial.print(':');
        Serial.print(z);
        Serial.print('\n');*/
        
        if( handle_xyz != NULL ) handle_xyz(x*255,y*255,z*255);
      }
      
      if( data[SW_PAYLOAD_HDR_CONFIGMASK] & SW_DATA_GESTURE && data[SW_PAYLOAD_GESTURE] > 0){
        //Serial.println("Handling gesture...");
        // Valid gesture
        if( handle_gesture != NULL ) handle_gesture(data[SW_PAYLOAD_GESTURE]);
      }
      
      if ( data[SW_PAYLOAD_HDR_CONFIGMASK] & SW_DATA_TOUCH ){
        //Serial.println("Handling touch...");
        // Valid touch
        uint16_t touch_action = data[SW_PAYLOAD_TOUCH+1] << 8 | data[SW_PAYLOAD_TOUCH];
        uint16_t comp = 1 << 14;
        uint8_t x;
        for(x = 0; x < 16; x++){
          if( touch_action & comp ){
            if( handle_touch != NULL ) handle_touch(x);
            return;
          }
          comp = comp >> 1;
        }
      }
      
      if( data[SW_PAYLOAD_HDR_CONFIGMASK] & SW_DATA_AIRWHEEL && data[SW_PAYLOAD_HDR_SYSINFO] & SW_SYS_AIRWHEEL ){
        //Serial.println("Handling airwheel...");
        
        double delta = (data[SW_PAYLOAD_AIRWHEEL] - lastrotation) / 32.0;
        
        if( delta != 0 && delta > -0.5 and delta < 0.5 ){
          if( handle_airwheel != NULL ) handle_airwheel(delta * 360.0);  
        }
        lastrotation = data[SW_PAYLOAD_AIRWHEEL];
      }
}

SkyWriter sw;

void setup() {
  
  Serial.begin(9600);
  while(!Serial){};
  Serial.println("Hello world!");
  
  sw.begin(12, 13);
  sw.onTouch(touch);
  //sw.onAirwheel(airwheel);
  //sw.onGesture(gesture);
  //sw.onXYZ(xyz);


}

void xyz(unsigned char x, unsigned char y, unsigned char z){
  Serial.print(x);
  Serial.print(':');
  Serial.print(y);
  Serial.print(':');
  Serial.print(z);
  Serial.print('\n');
}

void gesture(unsigned char type){
  Serial.println("Got gesture ");
  Serial.print(type,DEC);
  Serial.print('\n');
}

void touch(unsigned char type){
  Serial.println("Got touch ");
  Serial.print(type,DEC);
  Serial.print('\n');
}

void airwheel(int delta){
  Serial.println("Got airwheel ");
  Serial.print(delta);
  Serial.print('\n');
}

void loop() {
  sw.poll();

}
