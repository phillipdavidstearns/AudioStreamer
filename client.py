import asyncio
import argparse
import signal
import pyaudio
import sys
import queue
import logging
from threading import Thread, Lock
from decouple import config
from time import sleep


def initialize_record_stream():
  global record_stream
  try:
    pyaudioObj = pyaudio.PyAudio()
    record_stream = pyaudioObj.open(
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

async def audio_stream_client(host='localhost', port=12345):
  global network_writer, sendQueue
  while True:
    while network_writer == None:
      try:
        reader, network_writer = await asyncio.open_connection(host, port)
      except Exception as e:
        logging.error(f"While establishing server connection: {e}")
      await asyncio.sleep(1)

    initialize_record_stream()

    try:
      while True:
        if data := sendQueue.get():
          network_writer.write(data)
          await network_writer.drain()
    except Exception as e:
      logging.error(f"While writing to socket: {e}")
      record_stream.stop_stream()
      sendQueue = queue.Queue()
      network_writer = None

# signal handler
def handler(signum, frame):
  global record_stream
  logging.info("Exiting the program")
  record_stream.stop_stream()
  if network_writer: network_writer.close()
  sys.exit(0) 

# define the callback function (called everytime there is input data)
def record(in_data, frame_count, time_info,  status):
  if network_writer:
    sendQueue.put(in_data)
  return (in_data, pyaudio.paContinue)

if __name__ == '__main__':

  # signal handler
  signal.signal(signal.SIGINT, handler)

  # command line arguments
  parser = argparse.ArgumentParser(description="AudioStream client")

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
    default=config('INPUT_DEVICE', cast=int, default=0),
    type=int
  )

  args = parser.parse_args()

  logging.basicConfig(format='[AudioStream CLIENT] - %(levelname)s | %(message)s', level=args.loglevel)

  logging.info(f"Host: {args.host}")
  logging.info(f"Port: {args.port}")
  logging.info(f"Size: {args.size} ms")

  # audio setup
  WIDTH = args.width
  FORMAT = pyaudio.get_format_from_width(WIDTH)
  CHANNELS = 1
  RATE = 44100
  CHUNK = 441 # 10 ms
  NUMCHUNKS = int(args.size / 10)

  record_stream = None
  network_writer = None
  sendQueue = queue.Queue() # store the audio data to send

  asyncio.run(audio_stream_client(
    host=args.host,
    port=args.port
  ))
