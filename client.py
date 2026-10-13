
import socket
import argparse
import signal
import pyaudio
import sys
import queue
import logging
from threading import Thread, Lock
from decouple import config
from time import sleep
'''
How should this work?
Start PyAudio Stream using the callback method to record audio from the ADC.

Threading vs Multiprocess?

Open a socket connection.
- Clear the queue
- Write audio to the queue
- If there's stuff in the queue contents over network
  - Max packet size?
Socket connection lost or closed?
- Stop writing audio to the queue
- Clear the queue
- Stop sending data
- Initiate a reconnection loop

TCP means all data arrives in sequence, but a little more overhead/latency

Compare use of queue in this project to TinyDragon queueing.


Basically there are two I/O related tasks:
- Capture audio from the ADC and place it in a queue (callbacks)
- Transmit that data over the network to the server
'''

class NetworkClient(Thread):
  def __init__(self, host='localhost', port='12345', protocol='tcp'):
    super().__init__()
    self.daemon = True
    self.lock = Lock()
    self.protocol = protocol
    self.host = host
    self.port = port
    self.socket = self.create_socket()
    self.do_run = False

  def create_socket(self):
    client_socket = None

    try:
      match self.protocol:
        case 'udp': 
          client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        case 'tcp':
          client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          client_socket.connect((self.host, self.port))
        case _:
          raise Exception(f"Unsupported protocol: {self.protocol}") 

      logging.info("Socket Initialized")
    except Exception as e:
      logging.error(f"While connecting to server: {e}")
      client_socket = None

    return client_socket

  def send(self, data):
    if not self.socket:
      logging.error(f"Socket not initialized. No Data Sent.")
      return

    try:
      match self.protocol:
        case 'udp':
          self.socket.sendto(data, (self.host, self.port))
        case 'tcp':
          self.socket.sendall(data)
        case _:
          raise Exception(f"Unsupported protocol: {self.protocol}") 
    except Exception as e:
      logging.error(f"[NetworkClient] While client was sending data: {e}")

  def run(self):
    logging.info('[NetworkClient] run()')
    self.do_run = True
    try:
      while self.do_run:
        sleep(0.1)
    except Exception as e:
      logging.error(f"[NetworkCLient] run(): {e}")

  def stop(self):
    try:
      logging.info('[NetworkClient] stop()')
      self.do_run=False
      if self.socket:
        self.socket.close()
        self.socket = None
    except Exception as e:
      logging.error(f"[NetworkClient] While closing socket: {repr(e)} ")
    finally:
      if self.is_alive():
        self.join()

# signal handler
def handler(signum, frame):
  global recordStream, client_socket
  logging.info("Exiting the program")
  recordStream.stop_stream()
  client.stop()
  sys.exit(0) 

# define the callback function (called everytime there is input data)
def record(data, frame_count, time_info,  status):
  if client.socket:
    logging.debug(f"Recording...")
    # sendQueue.put(data)

    try:
      
      client.send(data)
    except Exception as e:
      logging.error(f"While sending data: {e}")

  return (data, pyaudio.paContinue)

if __name__ == '__main__':

  # signal handler
  signal.signal(signal.SIGINT, handler)

  # command line arguments
  parser = argparse.ArgumentParser(description="AudioStream client")

  parser.add_argument(
    "--protocol",
    required=False,
    default=config('PROTOCOL', cast=str, default='udp'),
    choices=['udp', 'tcp']
  )

  parser.add_argument(
    "--host",
    required=False,
    default=config("HOST", cast=str, default="localhost")
  )

  parser.add_argument(
    "--port",
    required=False,
    default=config('PORT', cast=int, default=6047),
    type=int
  )

  parser.add_argument("--size", required=False, default=10, type=int, choices=range(10, 151, 10))

  parser.add_argument(
    "--loglevel",
    required=False,
    default=config('LOGLEVEL', cast=int, default=20),
    type=int,
    choices=[0,10,20,30,40,50]
  )

  parser.add_argument(
    "--device",
    required=False,
    default=config('INPUT_DEVICE', cast=int, default=0),
    type=int
  )

  args = parser.parse_args()

  logging.basicConfig(format='[AudioStream CLIENT] - %(levelname)s | %(message)s', level=args.loglevel)

  logging.info(f"Protocol: {args.protocol.upper()}")
  logging.info(f"Host: {args.host}")
  logging.info(f"Port: {args.port}")
  logging.info(f"Size: {args.size} ms")

  # audio setup
  FORMAT = pyaudio.paInt16
  CHANNELS = 1
  RATE = 44100
  CHUNK = 441 # 10 ms
  NUMCHUNKS = int(args.size / 10)

  sendQueue = queue.Queue() # store the audio data to send
  silence = 0
  silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS

  try:
    pyaudioObj = pyaudio.PyAudio()

    recordStream = pyaudioObj.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      input=True,
      frames_per_buffer=NUMCHUNKS * CHUNK,
      stream_callback=record,
      input_device_index=args.device
    )

    logging.info("PyAudio Device Initialized")
  except Exception as e:
    logging.error(f"While inializing audio device: {e}")
    sys.exit(1)


  # start streaming
  client = NetworkClient(
    host=args.host,
    port=args.port,
    protocol=args.protocol
  )
  client.start()

  while client.is_alive():
    sleep(0.1)
    # try:
    #   if sendData := sendQueue.get():
    #     client.send(sendData)
    # except Exception as e:
    #   logging.error(f"While sending data: {e}")






