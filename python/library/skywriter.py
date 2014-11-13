try:
    from smbus import SMBus
except ImportError:
    exit("This library requires python-smbus\nInstall with: sudo apt-get install python-smbus")

import threading, time, atexit, sys
import RPi.GPIO as GPIO

SW_ADDR = 0x42
SW_RESET_PIN = 17
SW_XFER_PIN  = 27

def i2c_bus_id():
  revision = ([l[12:-1] for l in open('/proc/cpuinfo','r').readlines() if l[:8]=="Revision"]+['0000'])[0]
  return 1 if int(revision, 16) >= 4 else 0

i2c = SMBus(i2c_bus_id())

GPIO.setmode(GPIO.BCM)
GPIO.setup(SW_RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

x = 0.0
y = 0.0
z = 0.0
rotation = 0
lastrotation = 0
gesture = 0

worker = None
on_gesture = []
on_move = []

def reset():
  GPIO.output(SW_RESET_PIN, GPIO.LOW)
  time.sleep(.1)
  GPIO.output(SW_RESET_PIN, GPIO.HIGH)
  time.sleep(3)

## Basic stoppable thread wrapper
#
#  Adds Event for stopping the execution loop
#  and exiting cleanly.
class StoppableThread(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.stop_event = threading.Event()
    self.daemon = True         

  def start(self):
    if self.isAlive() == False:
      self.stop_event.clear()
      threading.Thread.start(self)

  def stop(self):
    if self.isAlive() == True:
      # set event to signal thread to terminate
      self.stop_event.set()
      # block calling thread until thread really has terminated
      self.join()

## Basic thread wrapper class for asyncronously running functions
#
#  Basic thread wrapper class for running functions
#  asyncronously. Return False from your function
#  to abort looping.
class AsyncWorker(StoppableThread):
  def __init__(self, todo):
    StoppableThread.__init__(self)
    self.todo = todo

  def run(self):
    while self.stop_event.is_set() == False:
      if self.todo() == False:
        self.stop_event.set()
        break

def handle_sensor_data(data):
  global lastrotation, rotation
  '''
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
  '''
  d_size = data.pop(0)
  d_flags = data.pop(0)
  d_seq = data.pop(0)
  d_id = data.pop(0)
  
  d_configmask = data.pop(0) | data.pop(0) << 8
  d_timestamp  = data.pop(0)
  d_sysinfo    = data.pop(0)
  
  d_dspstatus = data[0:2]
  d_gesture   = data[2:6]
  d_touch     = data[6:10]
  d_airwheel  = data[10:12]
  d_xyz       = data[12:20]
  d_noisepow  = data[20:24]
 
  if d_configmask & 0b0000000000010000 and d_sysinfo & 0b0000001:
    # We have xyz info, and it's valid
    x, y, z = (
      (d_xyz[1] << 8 | d_xyz[0]) / 65536.0,
      (d_xyz[3] << 8 | d_xyz[2]) / 65536.0,
      (d_xyz[5] << 8 | d_xyz[4]) / 65536.0
    ) 
    #print( x, y, z )
  
  if d_configmask & 0b00000000000000010 and not d_gesture[0] & 0b00000001:
    # We have a gesture!
    is_edge = (d_gesture[3] & 0b00000001) > 0
    gestures = [
      ('garbage','',''),
      ('flick','west','east'),
      ('flick','east','west'),
      ('flick','south','north'),
      ('flick','north','south'),
      ('circle','clockwise',''),
      ('circle','counter-clockwise','')
    ]
    for i,gesture in enumerate(gestures):
      if d_gesture[0] == i + 1:
        print(gesture, is_edge)
        break

  if d_configmask & 0b00000000000000100:
    # We have a touch
    d_action = d_touch[1] << 8 | d_touch[0]
    d_touchcount = d_touch[2] * 5 # Time to touch in ms
    actions = [
      ('touch','south'),
      ('touch','west'),
      ('touch','north'),
      ('touch','east'),
      ('touch','center'),
      ('tap','south'),
      ('tap','west'),
      ('tap','north'),
      ('tap','east'),
      ('tap','center'),
      ('doubletap','south'),
      ('doubletap','west'),
      ('doubletap','north'),
      ('doubletap','east'),
      ('doubletap','center')
    ]
    comp = 0b0000000000000001
    for action in actions:
      if d_action & comp:
        print(action, d_touchcount)
        break
      comp = comp << 1

  if d_configmask & 0b0000000000001000 and d_sysinfo & 0b00000010:
    # Airwheel
    #rotation += d_airwheel[0] / 32.0
    #print('Airwheel:', rotation, (rotation * 360) % 360)
    if lastrotation > d_airwheel[0]:
      rotation -= (lastrotation - d_airwheel[0]) / 32.0
    if lastrotation < d_airwheel[0]:
      rotation += (d_airwheel[0] - lastrotation) / 32.0
    print('Airwheel:', rotation, (rotation * 360) % 360)
    lastrotation = d_airwheel[0]

    
  #fields = data[5] << data[4]
  #valid = data[7]

  #gesture = data[11] << 24 | data[10] << 16 | data[9] << 8 | data[8]

  '''if valid & 0b00000001:
    x, y, z = (
      (data[21] << 8 | data[20]) / 65536.0,
      (data[23] << 8 | data[22]) / 65536.0,
      (data[25] << 8 | data[24]) / 65536.0
    )
    for handler in on_move:
      handler(x, y, z)

    print(gesture, x, y, z)
   '''
def handle_status_info(data):
  error = data[7] << 8 | data[6]

def handle_firmware_info(data):
  pass

def _do_poll():
  if not GPIO.input(SW_XFER_PIN):
    '''
    Assert transfer line low to ensure
    MGC3130 doesn't update data buffers
    '''
    GPIO.setup(SW_XFER_PIN, GPIO.OUT, initial=GPIO.LOW)
    data = i2c.read_i2c_block_data(SW_ADDR, 0x00, 26)
    '''
    MSG | HEADER                  | PAYLOAD
        | size | flags | seq | ID | Depends on ID

    size: complete size of message, including header
    flags: reserved
    seq: Increments with each message sent
    ID: message ID
    '''
    message = data[3]
    if message == 0x91:
      handle_sensor_data(data)
    elif message == 0x15:
      handle_status_info(data)
    elif message == 0x83:
      handle_firmware_info(data)
    else:
      pass

    GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def start_poll():
  global worker
  if worker == None:
    worker = AsyncWorker(_do_poll)
  worker.start()

def stop_poll():
  global worker
  worker.stop()

def gesture():
  def register(handler):
    on_gesture.append(handler)
  return register

def move():
  def register(handler):
    on_move.append(handler)
  return register

def _exit():
  stop_poll()
  if GPIO != None:
    GPIO.cleanup()

atexit.register(_exit)

reset()
i2c.write_i2c_block_data(SW_ADDR, 0xa1, [0b00011111, 0b00011111])
start_poll()
