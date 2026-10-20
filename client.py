import asyncio
import argparse
import signal
import pyaudio
import sys
import logging
from decouple import config
from buffer import Buffer

#================================================================
# PyAudio Functions
#================================================================

# Closes the audio stream
def close_record_stream():
  global record_stream
  logging.debug(f"Closing record stream.")
  if record_stream:
    record_stream.close()
    record_stream = None

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
  close_record_stream()
  terminate_pyaudio()

#----------------------------------------------------------------

# The callback function used to fetch audio from the record stream when it is available
def record(in_data, frame_count, time_info,  status):
  if network_writer:
    buffer.put(in_data)
  return (in_data, pyaudio.paContinue)

#----------------------------------------------------------------

def initialize_record_stream():
  global pyaudio_obj, record_stream

  buffer.clear()

  try:
    pyaudio_obj = pyaudio.PyAudio()
    record_stream = pyaudio_obj.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      input=True,
      frames_per_buffer=CHUNK,
      stream_callback=record,
      input_device_index=args.device
    )

    logging.info("PyAudio Device Initialized")
  except Exception as e:
    logging.error(f"While inializing audio device: {e}")
    sys.exit(1)

#================================================================

async def audio_stream_client(host='localhost', port=12345):
  logging.info(f"Starting network stream.")

  global network_writer

  while True:
    while network_writer == None:
      try:
        reader, network_writer = await asyncio.open_connection(host, port)
      except OSError as e:
        logging.debug(f"OSError: {e}")
      except Exception as e:
        logging.error(f"While establishing server connection: {e}")
      await asyncio.sleep(1)

    logging.info(f"Connected to server @ {host}:{port}.")

    initialize_record_stream()

    try:
      while network_writer:
        if buffer.size() >= CHUNK * WIDTH:
          network_writer.write(buffer.get(CHUNK * WIDTH))
          await network_writer.drain()
    except Exception as e:
      logging.error(f"While writing to socket: {e}")
      network_writer = None
      shutdown_pyaudio()


#================================================================

# signal handler
def handler(signum, frame):
  logging.info("Exiting the program")
  shutdown_pyaudio()
  if network_writer: network_writer.close()
  sys.exit(0) 

#================================================================

if __name__ == '__main__':

  # signal handler
  signal.signal(signal.SIGINT, handler)

  #----------------------------------------------------------------

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

  parser.add_argument(
    "--blocksize",
    required=False,
    default=config('BLOCK_SIZE', cast=int, default=256),
    type=int
  )

  args = parser.parse_args()

  logging.basicConfig(
    format='[AudioStream CLIENT] - %(levelname)s | %(message)s',
    level=args.loglevel
  )
  logging.info(f"Block Size: {args.blocksize}")
  logging.info(f"Host: {args.host}")
  logging.info(f"Port: {args.port}")

  #----------------------------------------------------------------

  # audio setup
  WIDTH = args.width
  FORMAT = pyaudio.get_format_from_width(WIDTH)
  CHANNELS = 1
  RATE = 44100
  CHUNK = args.blocksize

  pyaudio_obj = None
  record_stream = None
  network_writer = None
  buffer = Buffer(zero_pad=False, send_empty=False)

  #----------------------------------------------------------------

  asyncio.run(audio_stream_client(
    host=args.host,
    port=args.port
  ))
