import atexit
import threading
import time
from sys import exit, version_info

try:
    from smbus import SMBus
except ImportError:
    if version_info[0] < 3:
        exit("This library requires python-smbus\nInstall with: sudo apt-get install python-smbus")
    elif version_info[0] == 3:
        exit("This library requires python3-smbus\nInstall with: sudo apt-get install python3-smbus")

try:
    import RPi.GPIO as GPIO
except ImportError:
    exit("This library requires the RPi.GPIO module\nInstall with: sudo pip install RPi.GPIO")

__version__ = '0.0.7'

SW_ADDR = 0x42
SW_RESET_PIN = 17
SW_XFER_PIN  = 27

SW_HEADER_SIZE   = 4

SW_DATA_DSP      = 0b0000000000000001
SW_DATA_GESTURE  = 0b0000000000000010
SW_DATA_TOUCH    = 0b0000000000000100
SW_DATA_AIRWHEEL = 0b0000000000001000
SW_DATA_XYZ      = 0b0000000000010000

SW_SYSTEM_STATUS = 0x15
SW_REQUEST_MSG   = 0x06
SW_FW_VERSION    = 0x83
SW_SET_RUNTIME   = 0xA2
SW_SENSOR_DATA   = 0x91

i2c_bus = 0

if GPIO.RPI_REVISION == 2 or GPIO.RPI_REVISION == 3:
    i2c_bus = 1

i2c = SMBus(i2c_bus)
    
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SW_RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

x = 0.0
y = 0.0
z = 0.0
rotation = 0.0
lastrotation = 0.0
gesture = 0

io_error_count = 0

worker = None
_on_flick    = None
_on_move     = None
_on_airwheel = []
_on_touch    = {}
_on_touch_repeat = {}
_on_touch_last   = {}
_on_garbage  = None
_on_circle   = {}

def millis():
  return int(round(time.time() * 1000))

def reset():
  GPIO.output(SW_RESET_PIN, GPIO.LOW)
  time.sleep(.1)
  GPIO.output(SW_RESET_PIN, GPIO.HIGH)
  time.sleep(.5) # Datasheet delay of 200ms plus change
  #time.sleep(3)

class StoppableThread(threading.Thread):
  '''
  Basic stoppable thread wrapper

  Adds Event for stopping the execution loop
  and exiting cleanly.
  '''
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


class AsyncWorker(StoppableThread):
  '''
  Basic thread wrapper class for asyncronously running functions

  Basic thread wrapper class for running functions
  asyncronously. Return False from your function
  to abort looping.
  '''
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
  
  d_configmask = data.pop(0) | data.pop(0) << 8
  d_timestamp  = data.pop(0) # 200hz, 8-bit counter, max ~1.25sec
  d_sysinfo    = data.pop(0)
  
  d_dspstatus = data[0:2]
  d_gesture   = data[2:6]
  d_touch     = data[6:10]
  d_airwheel  = data[10:12]
  d_xyz       = data[12:20]
  d_noisepow  = data[20:24]
 
  if d_configmask & SW_DATA_XYZ and d_sysinfo & 0b0000001:
    # We have xyz info, and it's valid
    x, y, z = (
      (d_xyz[1] << 8 | d_xyz[0]) / 65536.0,
      (d_xyz[3] << 8 | d_xyz[2]) / 65536.0,
      (d_xyz[5] << 8 | d_xyz[4]) / 65536.0
    ) 
    if callable(_on_move):
      _on_move(x, y, z)
    #print( x, y, z )
  
  if d_configmask & SW_DATA_GESTURE and not d_gesture[0] == 0:
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

        if gesture[0] == 'flick' and callable(_on_flick):
          _on_flick(gesture[1], gesture[2])

        break

  if d_configmask & SW_DATA_TOUCH:
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

    comp = 0b0000000000000001 << len(actions)-1
    for action in reversed(actions):
      if d_action & comp:

        handle_touch = False
        if action[0] in _on_touch.keys() and action[1] in _on_touch[action[0]].keys():
          if not action[0] in _on_touch_last.keys():
            _on_touch_last[action[0]] = {}
            handle_touch = True
          if not action[1] in _on_touch_last[action[0]].keys():
            _on_touch_last[action[0]][action[1]] = None
            handle_touch = True

          elif (millis() - _on_touch_last[action[0]][action[1]]) >= 1000.0 / _on_touch_repeat[action[0]][action[1]]:
            handle_touch = True

          if callable(_on_touch[action[0]][action[1]]) and handle_touch:
            _on_touch[action[0]][action[1]]()
            _on_touch_last[action[0]][action[1]] = millis()

        if action[0] in _on_touch.keys() and 'all' in _on_touch[action[0]].keys():
          if not action[0] in _on_touch_last.keys():
            _on_touch_last[action[0]] = {}
            handle_touch = True
          if not 'all' in _on_touch_last[action[0]].keys():
            _on_touch_last[action[0]]['all'] = None
            handle_touch = True
          elif (millis() - _on_touch_last[action[0]]['all']) >= 1000.0 / _on_touch_repeat[action[0]]['all']:
            handle_touch = True

          if callable(_on_touch[action[0]]['all']) and handle_touch:
            _on_touch[action[0]]['all'](action[1])
            _on_touch_last[action[0]]['all'] = millis()

        break
      comp = comp >> 1

  if d_configmask & SW_DATA_AIRWHEEL and d_sysinfo & 0b00000010:
    # Airwheel
    delta = (d_airwheel[0] - lastrotation) / 32.0
    '''
    Delta is in degrees, with 1 = full 360 degree rotation
    Positive numbers equal clockwise delta, negative are counter-clockwise
    '''
    if delta != 0 and delta > -0.5 and delta < 0.5:
      if callable(_on_airwheel):
        _on_airwheel(delta * 360.0)

      rotation += delta
      if rotation < 0:
        rotation = 0
      if rotation > 1000:
        rotation = 1000
    lastrotation = d_airwheel[0]
'''
    if lastrotation > d_airwheel[0]:
      rotation -= (lastrotation - d_airwheel[0]) / 32.0
    if lastrotation < d_airwheel[0]:
      rotation += (d_airwheel[0] - lastrotation) / 32.0
    print('Airwheel:', rotation, (rotation * 360) % 360)
    lastrotation = d_airwheel[0]
'''
def handle_status_info(data):
  error = data[7] << 8 | data[6]

def handle_firmware_info(data):
  print('Got firmware info')

  d_fw_valid = data.pop(0)
  d_hw_rev = data.pop(0) | data.pop(0) << 8
  d_param_st = data.pop(0)
  d_loader_version = [ data.pop(0), data.pop(0), data.pop(0) ],
  d_fw_st = data.pop(0)
  d_fw_version = ''.join(map(chr,data))

  print(d_fw_version)

  if d_fw_valid == 0:
    raise Exception("No valid GestIC Library could be located")

  if d_fw_valid == 0x0A:
    raise Exception("An invalid GestiIC Library was stored, or the last update failed")

def _do_poll():
  global io_error_count
  time.sleep(0.001)
  if not GPIO.input(SW_XFER_PIN):
    '''
    Assert transfer line low to ensure
    MGC3130 doesn't update data buffers
    '''
    GPIO.setup(SW_XFER_PIN, GPIO.OUT, initial=GPIO.LOW)
    try:
      data = i2c.read_i2c_block_data(SW_ADDR, 0x00, 26)
      io_error_count = 0
    except IOError:
      io_error_count += 1
      if io_error_count > 10:
        raise Exception("Skywriter encoutered nore than 10 consecutive I2C IO errors!")
      return


    '''
    MSG | HEADER                  | PAYLOAD
        | size | flags | seq | ID | Depends on ID

    size: complete size of message, including header
    flags: reserved
    seq: Increments with each message sent
    ID: message ID
    '''
    d_size  = data.pop(0)
    d_flags = data.pop(0)
    d_seq   = data.pop(0)
    d_ident = data.pop(0)

    if   d_ident == 0x91:
      handle_sensor_data(data)
    elif d_ident == 0x15:
      handle_status_info(data)
    elif d_ident == 0x83:
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

def get_arg(args, arg, default = None):
  if arg in args.keys():
    return args[arg]
  return default

def flick(*args, **kwargs):
  def register(handler):
    global _on_flick
    _on_flick = handler
  return register


def touch(*args, **kwargs):
  '''
  Bind touch event

  Keyword Arguments:
  repeat_rate - Max number of times/second to fire the touch event
  position - Position of touch to watch- north, south, east, west, center
  '''
  global _on_touch, _on_touch_repeat

  t_position = get_arg(kwargs, 'position', 'all')
  t_repeat_rate = get_arg(kwargs, 'repeat_rate', 4)

  if not 'touch' in _on_touch.keys():
    _on_touch['touch'] = {}
  if not 'touch' in _on_touch_repeat.keys():
    _on_touch_repeat['touch'] = {}

  def register(handler):
    global _on_touch, _on_touch_repeat
    _on_touch['touch'][t_position] = handler
    _on_touch_repeat['touch'][t_position] = t_repeat_rate

  return register


def tap(*args, **kwargs):
  '''
  Bind tap event

  Keyword Arguments:
  repeat_rate - Max number of times/second to fire the touch event
  position - Position of tap to watch- north, south, east, west, center
  '''
  global _on_touch, _on_touch_repeat

  t_position = get_arg(kwargs, 'position', 'all')
  t_repeat_rate = get_arg(kwargs, 'repeat_rate', 4)

  if not 'tap' in _on_touch.keys():
    _on_touch['tap'] = {}
  if not 'tap' in _on_touch_repeat.keys():
    _on_touch_repeat['tap'] = {}

  def register(handler):
    global _on_touch, _on_touch_repeat
    _on_touch['tap'][t_position] = handler
    _on_touch_repeat['tap'][t_position] = t_repeat_rate

  return register


def double_tap(*args, **kwargs):
  '''
  Bind double tap event

  Keyword Arguments:
  repeat_rate - Max number of times/second to fire the double tap event
  position - Position of double tap to watch- north, south, east, west, center
  '''
  global _on_touch, _on_touch_repeat

  t_position = get_arg(kwargs, 'position', 'all')
  t_repeat_rate = get_arg(kwargs, 'repeat_rate', 4)

  if not 'doubletap' in _on_touch.keys():
    _on_touch['doubletap'] = {}
  if not 'doubletap' in _on_touch_repeat.keys():
    _on_touch_repeat['doubletap'] = {}

  def register(handler):
    global _on_touch
    _on_touch['doubletap'][t_position] = handler
    _on_touch_repeat['doubletap'][t_position] = t_repeat_rate

  return register


def garbage():
  '''
  Bind an action to the "garbage" gesture
  A sort of grab-and-throw-away-garbage above the Skywriter
  '''
  def register(handler):
    global _on_garbage
    _on_garbage = handler
  return register


def move():
  '''
  Bind an action to move

  The handler will receive x, y and z values
  describing the tracked finger in 3D space above
  the Skywriter.
  '''
  def register(handler):
    global _on_move
    _on_move = handler
  return register


def airwheel():
  '''
  Bind an action to the "airhweel" gesture

  Point your finger at the Skywriter and spin it in a wheel
  The handler will receive a rotation delta in degrees
  '''
  def register(handler):
    global _on_airwheel
    _on_airwheel = handler
  return register


def _exit():
  stop_poll()
  if GPIO != None:
    GPIO.cleanup()


atexit.register(_exit)


reset()
i2c.write_i2c_block_data(SW_ADDR, 0xa1, [0b00000000, 0b00011111, 0b00000000, 0b00011111])
start_poll()
