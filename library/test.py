import sys
import mock

sys.modules['RPi'] = mock.Mock()
sys.modules['RPi.GPIO'] = mock.Mock()
sys.modules['smbus'] = mock.Mock()

import skywriter

@skywriter.airwheel()
def airwheel(delta):
    print(delta)

@skywriter.move()
def move(x,y,z):
    print(x,y,z)
