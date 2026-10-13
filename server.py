import asyncio
import socket
import argparse
import signal
import pyaudio
import sys
import logging
from threading import Thread, Lock
from decouple import config
from time import sleep

'''
How should this work?
Start PyAudio Stream using the callback method to playback audio received over the network.
Open a socket connection and wait for incomming data.

Threading vs Multiprocess?

TCP means all data arrives in sequence, but a little more overhead/latency
  - If there's no connection or if an exception is raised, output silence
    - Flag active connection
      - if exception is raised and flag was active, reset the socket 
      - clear the flag

  - If the buffer doesn't contain a full chunk
    - write zeros to audio buffer?
    - wait until full chunk is available?
    - zero-pad incomplete chunk?
    - make each a argument/setting choice?

Use TinyDragon as an example of how to handle the incomming data.
  - Perhaps the queue module ixn client.py is useful.

Basically there are two I/O related tasks:
- Receive data from a connected client and put it in a queue (non-blocking process/thread)
- Read data out of the queue into the audio buffer (callbacks)
'''

async def handle_client(reader, writer):
  while True:
    if data := await reader.read(65536):
      buffer.put(data)
    else:
      break

async def start_server(port):
  server = await asyncio .start_server(
    handle_client, '0.0.0.0', port
  )
  async with server:
    await server.serve_forever()

# signal handler
def handler(signum, frame):
  logging.info("Exiting the program")
  playStream.stop_stream()
  sys.exit(0)

def play(data, frame_count, time_info, status):
  logging.debug(f"PyAudio stream wants {frame_count} frames.")
  data = buffer.get(frame_count * WIDTH)
  return(bytes(data), pyaudio.paContinue)

class Buffer:
  def __init__(self, size_limit=7056000):
    self.buffer = bytearray()
    self.size_limit = size_limit

  def clearBuffer(self):
    self.buffer = bytearray()

  def get(self, qty_bytes):
    data = self.buffer[:qty_bytes]
    self.buffer = self.buffer[qty_bytes:]
    data += bytes([0]) * (qty_bytes - len(data))
    return data

  def put(self, data):
    if len(self.buffer) < self.size_limit:
      self.buffer.extend(data)

if __name__ == '__main__':
  buffer = Buffer()

  # signal handler
  signal.signal(signal.SIGINT, handler)

  # command line arguments
  parser=argparse.ArgumentParser(description="AudioStream server")

  parser.add_argument(
    "--protocol",
    required=False,
    default=config('PROTOCOL', cast=str, default='udp'),
    choices=['udp', 'tcp']
  )

  parser.add_argument(
    "--port",
    required=False,
    default=config('PORT', cast=int, default=6047),
    type=int
  )

  parser.add_argument(
    "--width",
    required=False,
    default=2,
    type=int,
    choices=range(1,4)
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
    default=config('OUTPUT_DEVICE', cast=int, default=0),
    type=int
  )

  args=parser.parse_args()

  logging.basicConfig(format='[AudioStream SERVER] - %(levelname)s | %(message)s', level=args.loglevel)

  logging.info(f"Protocol: {args.protocol.upper()}")
  logging.info(f"Port: {args.port}")
  logging.info(f"Size: {args.size} ms")
  logging.info(f"Device: {args.device}")

  # audio setup
  WIDTH = args.width
  FORMAT = pyaudio.get_format_from_width(WIDTH)
  CHANNELS = 1
  RATE = 44100
  CHUNK = 441 # 10 ms
  NUMCHUNKS = int(args.size / 10)

  silence = 0
  silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS
  server = None

  try:

    pyaudioObj = pyaudio.PyAudio()

    playStream = pyaudioObj.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      output=True,
      frames_per_buffer=CHUNK * NUMCHUNKS,
      output_device_index=args.device,
      stream_callback=play
    )

    logging.info("PyAudio Device Initialized")
  except Exception as e:
    logging.error(f"While inializing audio device: {e}")
    sys.exit(1)

  asyncio.run(start_server(args.port))