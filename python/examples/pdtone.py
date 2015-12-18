import os, socket, time, subprocess, atexit, tempfile

class PDTone():
  def __init__(self, pd_file=None):
    self.port = 3000
    self.addr = '127.0.0.1' #'192.168.1.86'
    self.tempfile = None
    if pd_file == None:
      self.tempfile, self.pd_file = tempfile.mkstemp()
      self.create_pd_file()
    else:
      self.pd_file = pd_file
    self.pid = None
    self.proc_pd = None

    atexit.register(self.stop_pd)

    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    self.start_pd()
    self.connect()

  def start_pd(self):
    pdfile = os.path.join(os.getcwd(), self.pd_file)
    self.proc_pd = subprocess.Popen(['/usr/bin/pd', '-nogui', pdfile], stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
    pid = subprocess.check_output(['/bin/pidof','pd'], )
    time.sleep(0.5)
    self.pid = int(pid.split(' ')[0])
    print("Started PD with PID: " + str(pid) + " File: " + pdfile)
  
  def connect(self):
    attempts = 30
    while attempts:
      print("Attempting to connect to PD")
      try:
        self.socket.connect((self.addr,self.port))
        print("Connected to PD")
        break
      except socket.error:
        time.sleep(1)
      attempts-=1

  def stop_pd(self):
    if self.proc_pd != None:
      print("Killing PD instance")
      self.proc_pd.terminate()
      self.proc_pd = None
      self.pid = None
    if self.tempfile != None:
      print("Removing temp file")
      os.close(self.tempfile)
      os.remove(self.pd_file)

  def send(self, cmd):
    self.socket.send(cmd + ';')

  def power_on(self):
    self.send('power 1')

  def power_off(self):
    self.send('power 0')
 
  def custom(self, k, f):
    self.send(k + ' ' + str(f))
  
  def tone(self, f):
    self.send('tone ' + str(f))

  def note(self, f, duration):
    self.tone(f)
    self.power_on()
    time.sleep(duration)
    self.power_off()

  def create_pd_file(self):
    print("Populating temp PD file: " + self.pd_file)
    f = open(self.pd_file, 'w')
    f.write("#N canvas 42 59 994 720 10;")
    f.write("#X obj 244 545 dac~;")
    f.write("#X obj 547 131 netreceive " + str(self.port) + ";")
    f.write("#X obj 548 168 route x y z volume power;")
    f.write("#X obj 542 209 s x;")
    f.write("#X obj 583 216 s y;")
    f.write("#X obj 624 218 s z;")
    f.write("#X obj 680 249 s volume;")
    f.write("#X obj 778 245 s power;")
    f.write("#X obj 371 158 r z;")
    f.write("#X obj 371 264 phasor~;")
    f.write("#X obj 247 447 +~;")
    f.write("#X obj 211 144 +~ 400;")
    f.write("#X obj 113 143 +~ 400;")
    f.write("#X obj 117 249 phasor~;")
    f.write("#X obj 212 256 phasor~;")
    f.write("#X obj 210 183 -~ 4;")
    f.write("#X obj 294 70 r y;")
    f.write("#X obj 291 110 * 0.008;")
    f.write("#X obj 109 106 *~ 0.6;")
    f.write("#X obj 211 109 *~ 0.6;")
    f.write("#X obj 210 79 r z;")
    f.write("#X obj 109 76 r z;")
    f.write("#X obj 371 227 +~ 400;")
    f.write("#X obj 371 194 *~ 0.6;")
    f.write("#X obj 371 315 bp~ 660 0.1;")
    f.write("#X obj 371 412 *~ 0.15;")
    f.write("#X obj 294 391 r x;")
    f.write("#X obj 249 514 bp~ 800 0.99;")
    f.write("#X obj 251 481 *~ 0.5;")
    f.write("#X obj 301 453 * 0.001;")
    f.write("#X obj 559 364 tgl 15 0 empty empty empty 17 7 0 10 -262144 -1 -1 0")
    f.write("300;")
    f.write("#X obj 549 312 r power;")
    f.write("#X msg 555 418 \; pd dsp \$1 \;;")
    f.write("#X obj 371 375 *~ 0.12;")
    f.write("#X obj 212 322 *~ 0.5;")
    f.write("#X obj 120 340 *~ 0.5;")
    f.write("#X connect 1 0 2 0;")
    f.write("#X connect 2 0 3 0;")
    f.write("#X connect 2 1 4 0;")
    f.write("#X connect 2 2 5 0;")
    f.write("#X connect 2 3 6 0;")
    f.write("#X connect 2 4 7 0;")
    f.write("#X connect 8 0 23 0;")
    f.write("#X connect 9 0 24 0;")
    f.write("#X connect 10 0 28 0;")
    f.write("#X connect 11 0 15 0;")
    f.write("#X connect 12 0 13 0;")
    f.write("#X connect 13 0 35 0;")
    f.write("#X connect 14 0 34 0;")
    f.write("#X connect 15 0 14 0;")
    f.write("#X connect 16 0 17 0;")
    f.write("#X connect 17 0 15 1;")
    f.write("#X connect 18 0 12 0;")
    f.write("#X connect 19 0 11 0;")
    f.write("#X connect 20 0 19 0;")
    f.write("#X connect 21 0 18 0;")
    f.write("#X connect 22 0 9 0;")
    f.write("#X connect 23 0 22 0;")
    f.write("#X connect 24 0 33 0;")
    f.write("#X connect 25 0 10 0;")
    f.write("#X connect 26 0 29 0;")
    f.write("#X connect 27 0 0 0;")
    f.write("#X connect 27 0 0 1;")
    f.write("#X connect 28 0 27 0;")
    f.write("#X connect 29 0 28 1;")
    f.write("#X connect 30 0 32 0;")
    f.write("#X connect 31 0 30 0;")
    f.write("#X connect 33 0 25 0;")
    f.write("#X connect 34 0 10 0;")
    f.write("#X connect 35 0 10 0;")
    f.close()
