import atexit
import threading
import time
from sys import version_info

try:
    from smbus import SMBus
except ImportError:
    if version_info[0] < 3:
        raise ImportError("This library requires python-smbus\nInstall with: sudo apt-get install python-smbus")
    elif version_info[0] == 3:
        raise ImportError("This library requires python3-smbus\nInstall with: sudo apt-get install python3-smbus")

try:
    import RPi.GPIO as GPIO
except ImportError:
    raise ImportError("This library requires the RPi.GPIO module\nInstall with: sudo pip install RPi.GPIO")

__version__ = '0.0.8'

SW_ADDR = 0x42
SW_RESET_PIN = 17
SW_XFER_PIN = 27

SW_HEADER_SIZE = 4

SW_DATA_DSP = 0b0000000000000001
SW_DATA_GESTURE = 0b0000000000000010
SW_DATA_TOUCH = 0b0000000000000100
SW_DATA_AIRWHEEL = 0b0000000000001000
SW_DATA_XYZ = 0b0000000000010000

SW_SYSTEM_STATUS = 0x15
SW_REQUEST_MSG = 0x06
SW_FW_VERSION = 0x83
SW_SET_RUNTIME = 0xA2
SW_SENSOR_DATA = 0x91

i2c_bus = 0
i2c = None

if GPIO.RPI_REVISION == 2 or GPIO.RPI_REVISION == 3:
    i2c_bus = 1


x = 0.0
y = 0.0
z = 0.0
rotation = 0.0
_lastrotation = 0.0
_round_to = 4
_enable_auto_calibration = False
_enable_events = True
_debug = False
gesture = 0

io_error_count = 0

_worker = None
_on_flick = None
_on_move = None
_on_airwheel = []
_on_touch = {}
_on_touch_repeat = {}
_on_touch_last = {}
_on_garbage = None
_on_circle = {}
_is_setup = False


def millis():
    return int(round(time.time() * 1000))


def reset():
    GPIO.output(SW_RESET_PIN, GPIO.LOW)
    time.sleep(.1)
    GPIO.output(SW_RESET_PIN, GPIO.HIGH)
    time.sleep(.5)  # Datasheet delay of 200ms plus change


def enable(status=True):
    global _enable_events
    _enable_events = status


class StoppableThread(threading.Thread):
    '''Basic stoppable thread wrapper

    Adds Event for stopping the execution loop
    and exiting cleanly.
    '''
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        self.daemon = True

    def alive(self):
        try:
            return self.isAlive()
        except AttributeError:
            # Python >= 3.9
            return self.is_alive()

    def start(self):
        if not self.alive():
            self.stop_event.clear()
            threading.Thread.start(self)

    def stop(self):
        if self.alive():
            # set event to signal thread to terminate
            self.stop_event.set()
            # block calling thread until thread really has terminated
            self.join()


class AsyncWorker(StoppableThread):
    '''Basic thread wrapper class for asyncronously running functions

    Basic thread wrapper class for running functions
    asyncronously. Return False from your function
    to abort looping.
    '''
    def __init__(self, todo):
        StoppableThread.__init__(self)
        self.todo = todo

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            if not self.todo():
                self.stop_event.set()
                break


def _handle_sensor_data(data):
    global _lastrotation, rotation

    d_configmask = data.pop(0) | data.pop(0) << 8
    # d_timestamp = data.pop(0)  # 200hz, 8-bit counter, max ~1.25sec
    d_sysinfo = data.pop(0)

    # d_dspstatus = data[0:2]
    d_gesture = data[2:6]
    d_touch = data[6:10]
    d_airwheel = data[10:12]
    d_xyz = data[12:20]
    # d_noisepow = data[20:24]

    if d_configmask & SW_DATA_XYZ and d_sysinfo & 0b0000001:
        # We have xyz info, and it's valid
        x, y, z = (
            round((d_xyz[1] << 8 | d_xyz[0]) / 65536.0, _round_to),
            round((d_xyz[3] << 8 | d_xyz[2]) / 65536.0, _round_to),
            round((d_xyz[5] << 8 | d_xyz[4]) / 65536.0, _round_to)
        )
        if callable(_on_move):
            _on_move(x, y, z)

    if d_configmask & SW_DATA_GESTURE and not d_gesture[0] == 0:
        # We have a gesture!
        # is_edge = (d_gesture[3] & 0b00000001) > 0
        gestures = [
            ('garbage', '', ''),
            ('flick', 'west', 'east'),
            ('flick', 'east', 'west'),
            ('flick', 'south', 'north'),
            ('flick', 'north', 'south'),
            ('circle', 'clockwise', ''),
            ('circle', 'counter-clockwise', '')
        ]
        for i, gesture in enumerate(gestures):
            if d_gesture[0] == i + 1:

                if gesture[0] == 'flick' and callable(_on_flick):
                    _on_flick(gesture[1], gesture[2])

                break

    if d_configmask & SW_DATA_TOUCH:
        # We have a touch
        d_action = d_touch[1] << 8 | d_touch[0]

        # d_touchcount = d_touch[2] * 5 # Time to touch in ms
        actions = [
            ('touch', 'south'),
            ('touch', 'west'),
            ('touch', 'north'),
            ('touch', 'east'),
            ('touch', 'center'),
            ('tap', 'south'),
            ('tap', 'west'),
            ('tap', 'north'),
            ('tap', 'east'),
            ('tap', 'center'),
            ('doubletap', 'south'),
            ('doubletap', 'west'),
            ('doubletap', 'north'),
            ('doubletap', 'east'),
            ('doubletap', 'center')
        ]

        comp = 0b0000000000000001 << len(actions) - 1
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

                    if 'all' not in _on_touch_last[action[0]].keys():
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
        delta = (d_airwheel[0] - _lastrotation) / 32.0

        # Delta is in degrees, with 1 = full 360 degree rotation
        # Positive numbers equal clockwise delta, negative are counter-clockwise

        if delta != 0 and delta > -0.5 and delta < 0.5:
            if callable(_on_airwheel):
                _on_airwheel(delta * 360.0)

            rotation += delta

            if rotation < 0:
                rotation = 0

            if rotation > 1000:
                rotation = 1000

        _lastrotation = d_airwheel[0]


def _handle_status_info(data):
    # error = data[7] << 8 | data[6]
    pass


def _handle_firmware_info(data):
    print('Got firmware info')

    d_fw_valid = data.pop(0)
    # d_hw_rev = data.pop(0) | data.pop(0) << 8
    # d_param_st = data.pop(0)
    # d_loader_version = [ data.pop(0), data.pop(0), data.pop(0) ],
    # d_fw_st = data.pop(0)
    d_fw_version = ''.join(map(chr, data))

    print(d_fw_version)

    if d_fw_valid == 0:
        raise Exception("No valid GestIC Library could be located")

    if d_fw_valid == 0x0A:
        raise Exception("An invalid GestiIC Library was stored, or the last update failed")


def _do_poll() -> bool:
    global io_error_count

    time.sleep(0.001)

    if not _enable_events:
        return True

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
            return False

        # d_size = data.pop(0)
        # d_flags = data.pop(0)
        # d_seq = data.pop(0)
        d_ident = data.pop(0)

        if d_ident == 0x91:
            _handle_sensor_data(data)

        elif d_ident == 0x15:
            _handle_status_info(data)

        elif d_ident == 0x83:
            _handle_firmware_info(data)

        else:
            pass

        GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    return True


def _start_poll():
    global _worker
    if _worker is None:
        _worker = AsyncWorker(_do_poll)
    _worker.start()


def _stop_poll():
    global _worker
    if _worker is not None:
        _worker.stop()
        _worker = None


def flick(*args, **kwargs):
    '''Bind flick event'''

    setup()

    def register(handler):
        global _on_flick
        _on_flick = handler

    return register


def touch(*args, **kwargs):
    '''Bind touch event

    :param repeat_rate: Max number of times/second to fire the touch event
    :param position: Position of touch to watch- north, south, east, west, center
    '''
    global _on_touch, _on_touch_repeat

    setup()

    t_position = kwargs.get('position', 'all')
    t_repeat_rate = kwargs.get('repeat_rate', 4)

    if 'touch' not in _on_touch.keys():
        _on_touch['touch'] = {}
    if 'touch' not in _on_touch_repeat.keys():
        _on_touch_repeat['touch'] = {}

    def register(handler):
        global _on_touch, _on_touch_repeat
        _on_touch['touch'][t_position] = handler
        _on_touch_repeat['touch'][t_position] = t_repeat_rate

    return register


def tap(*args, **kwargs):
    '''Bind tap event

    :param repeat_rate: Max number of times/second to fire the touch event
    :param position: Position of tap to watch- north, south, east, west, center
    '''
    global _on_touch, _on_touch_repeat

    setup()

    t_position = kwargs.get('position', 'all')
    t_repeat_rate = kwargs.get('repeat_rate', 4)

    if 'tap' not in _on_touch.keys():
        _on_touch['tap'] = {}
    if 'tap' not in _on_touch_repeat.keys():
        _on_touch_repeat['tap'] = {}

    def register(handler):
        global _on_touch, _on_touch_repeat
        _on_touch['tap'][t_position] = handler
        _on_touch_repeat['tap'][t_position] = t_repeat_rate

    return register


def double_tap(*args, **kwargs):
    '''Bind double tap event

    :param repeat_rate: Max number of times/second to fire the double tap event
    :param position: Position of double tap to watch- north, south, east, west, center
    '''
    global _on_touch, _on_touch_repeat

    setup()

    t_position = kwargs.get('position', 'all')
    t_repeat_rate = kwargs.get('repeat_rate', 4)

    if 'doubletap' not in _on_touch.keys():
        _on_touch['doubletap'] = {}
    if 'doubletap' not in _on_touch_repeat.keys():
        _on_touch_repeat['doubletap'] = {}

    def register(handler):
        global _on_touch
        _on_touch['doubletap'][t_position] = handler
        _on_touch_repeat['doubletap'][t_position] = t_repeat_rate

    return register


def garbage():
    '''Bind an action to the "garbage" gesture

    A sort of grab-and-throw-away-garbage above the Skywriter
    '''

    setup()

    def register(handler):
        global _on_garbage
        _on_garbage = handler

    return register


def move():
    '''Bind an action to move

    The handler will receive x, y and z values
    describing the tracked finger in 3D space above
    the Skywriter.
    '''

    setup()

    def register(handler):
        global _on_move
        _on_move = handler

    return register


def airwheel():
    '''Bind an action to the "airhweel" gesture

    Point your finger at the Skywriter and spin it in a wheel
    The handler will receive a rotation delta in degrees
    '''

    setup()

    def register(handler):
        global _on_airwheel
        _on_airwheel = handler

    return register


def _exit():
    _stop_poll()
    if GPIO is not None:
        GPIO.cleanup()


def setup():
    global i2c, _is_setup

    if _is_setup:
        return True

    _is_setup = True

    i2c = SMBus(i2c_bus)

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SW_RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    atexit.register(_exit)

    def print_hex(data):
        if _debug:
            print(" ".join([hex(x) for x in data]))

    def get_status(id):
        for x in range(10):
            time.sleep(0.001)
            GPIO.setup(SW_XFER_PIN, GPIO.OUT, initial=GPIO.LOW)
            data = i2c.read_i2c_block_data(SW_ADDR, 0x00, 26)
            GPIO.setup(SW_XFER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            if data[3] == 0x15 and data[4] == id:
                print_hex(data)
                return True

        return False

    reset()

    #                                 Size  Flags  Seq   ID      Command        Reserved      Argument 0                     Argument 1
    # Command, Argument 1 and Argument 2 are sent LSByte first, so 1 = 0x01 0x00 etc

    # Enable AirWheel, requires 0x20 to be sent in Argument 0 and 1
    if _debug:
        print("Enable AirWheel")
    i2c.write_i2c_block_data(SW_ADDR, 0x10, [0x00, 0x00, 0xA2,   0x90, 0x00,    0x00, 0x00,  0x20, 0x00, 0x00, 0x00,         0x20, 0x00, 0x00, 0x00])  # noqa: E241
    if not get_status(0xA2):
        raise RuntimeError("Invalid response for SET_RUNTIME_PARAMETER")

    # Enable all gestures and X/Y/Z data, 0 = Garbage, 1 = Flick WE, 2 = Flick EW, 3 = Flick SN, 4 = Flick NS, 5 = Circle CW, 6 = Circle CCW
    if _debug:
        print("Enable all gestures")
    i2c.write_i2c_block_data(SW_ADDR, 0x10, [0x00, 0x00, 0xA2,   0x85, 0x00,    0x00, 0x00,   0b01111111, 0x00, 0x00, 0x00,  0b01111111, 0x00, 0x00, 0x00])  # noqa: E241
    if not get_status(0xA2):
        raise RuntimeError("Invalid response for SET_RUNTIME_PARAMETER")

    # Enable all data output 0 = DSP, 1 = Gesture, 2 = Touch, 3 = AirWheel, 4 = Position
    if _debug:
        print("Enable all data output")
    i2c.write_i2c_block_data(SW_ADDR, 0x10, [0x00, 0x00, 0xA2,   0xA0, 0x00,    0x00, 0x00,   0b00011111, 0x00, 0x00, 0x00,  0b00011111, 0x00, 0x00, 0x00])  # noqa: E241
    if not get_status(0xA2):
        raise RuntimeError("Invalid response for SET_RUNTIME_PARAMETER")

    # Disable auto-calibration
    if not _enable_auto_calibration:
        if _debug:
            print("Disable auto-calibration")
        i2c.write_i2c_block_data(SW_ADDR, 0x10, [0x00, 0x00, 0xA2,   0x80, 0x00,   0x00, 0x00,   0x00, 0x00, 0x00, 0x00,        0b00011111, 0x00, 0x00, 0x00])  # noqa: E241
        if not get_status(0xA2):
            raise RuntimeError("Invalid response for SET_RUNTIME_PARAMETER")

    _start_poll()
