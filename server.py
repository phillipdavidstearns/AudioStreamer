import asyncio
import argparse
import signal
import pyaudio
import sys
import logging
from decouple import config
from time import sleep

#================================================================
# PyAudio Functions
#================================================================

# Closes the audio stream
def close_play_stream():
  global play_stream
  logging.debug(f"Closing play stream.")
  if play_stream:
    play_stream.close()
    play_stream = None

#----------------------------------------------------------------

# Terminates the PyAudio session and releases resources
def terminate_pyaudio():
  logging.debug(f"Terminating PyAudio Session.")
  global pyaudio_obj
  if pyaudio_obj:
    pyaudio_obj.terminate()
    pyaudio_obj = None

#----------------------------------------------------------------

# Closes the active record stream and terminates pyaudio pbject
# Resets global variables to None
def shutdown_pyaudio():
  logging.info(f"Shutting down PyAudio.")
  close_play_stream()
  terminate_pyaudio()

#----------------------------------------------------------------

def play(data, frame_count, time_info, status):
  data = buffer.get(frame_count * WIDTH)
  return(bytes(data), pyaudio.paContinue)

#================================================================

async def handle_client(reader, writer):
  logging.debug(f"Connection established.")
  buffer.clear()
  while True:
    if data := await reader.read(65536):
      buffer.put(data)
    else:
      logging.debug(f"Connection closed.")
      break

async def start_server(host='localhost', port=12345):
  server = await asyncio.start_server(
    handle_client, host, port, keep_alive=True
  )
  async with server:
    await server.serve_forever()

#================================================================

# signal handler
def handler(signum, frame):
  logging.info("Exiting the program")
  shutdown_pyaudio()
  sys.exit(0)

#================================================================

class Buffer:
  def __init__(self, size_limit=7056000):
    self.buffer = bytearray()
    self.size_limit = size_limit

  def clear(self):
    self.buffer = bytearray()

  def get(self, qty_bytes):
    data = self.buffer[:qty_bytes]
    self.buffer = self.buffer[qty_bytes:]
    if qty_bytes != len(data):
      data += bytes([0]) * (qty_bytes - len(data))
    return data

  def put(self, data):
    if len(self.buffer) < self.size_limit:
      self.buffer.extend(data)

#================================================================

if __name__ == '__main__':
  # signal handler
  signal.signal(signal.SIGINT, handler)

  #----------------------------------------------------------------

  # command line arguments
  parser=argparse.ArgumentParser(description="AudioStream server")

  parser.add_argument(
    "--host",
    required=False,
    default=config('SERVER_ADDRESS', cast=str, default='localhost'),
    type=str
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

  logging.info(f"Server address: {args.host}")
  logging.info(f"Port: {args.port}")
  logging.info(f"Size: {args.size} ms")
  logging.info(f"Device: {args.device}")

  #----------------------------------------------------------------

  # audio setup
  WIDTH = args.width
  FORMAT = pyaudio.get_format_from_width(WIDTH)
  CHANNELS = 1
  RATE = 44100
  CHUNK = 441 # 10 ms
  NUMCHUNKS = int(args.size / 10)

  buffer = Buffer()

  #----------------------------------------------------------------

  try:

    pyaudio_obj = pyaudio.PyAudio()
    play_stream = pyaudio_obj.open(
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
    shutdown_pyaudio()
    sys.exit(1)

  #----------------------------------------------------------------

  asyncio.run(start_server(
    host=args.host,
    port=args.port
  ))
