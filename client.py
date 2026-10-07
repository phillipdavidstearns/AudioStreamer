import socket
import argparse
import signal
import pyaudio
import sys
import queue
import logging
from decouple import config

# signal handler
def handler(signum, frame):
  global recordStream, client_socket
  logging.info("Exiting the program")
  recordStream.stop_stream()
  client_socket.close()
  sys.exit(0) 

# define the callback function (called everytime there is input data)
def record(data, frame_count, time_info,  status):
  global sendQueue
  sendQueue.put(data)
  return (silenceData, pyaudio.paContinue)

def sendAudio():
  global client_socket, destination, sequenceNumber, sendQueue

  audioData = sendQueue.get()

  seqBytes = sequenceNumber.to_bytes(2, byteorder="little", signed=False)

  sendData = seqBytes + audioData

  logging.debug(f"Sending Sequence #{sequenceNumber} ({len(sendData)} bytes)")

  if args.protocol == 'udp':
      client_socket.sendto(sendData, destination)
  else:
      client_socket.sendall(sendData)

  sequenceNumber += 1

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
    default=config('DEVICE_INDEX', cast=int, default=0),
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

  # let's use a callback to read instead
  sendQueue = queue.Queue() # store the audio data to send

  # create a bogus silence data for the callback function
  silence = 0
  silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS

  sequenceNumber = 0

  try:
    pyaudioObj = pyaudio.PyAudio()

    recordStream = pyaudioObj.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      input=True,
      frames_per_buffer=NUMCHUNKS * CHUNK,
      stream_callback=record
    )

    logging.info("PyAudio Device Initialized")
  except Exception as e:
    logging.error(f"While inializing audio device: {e}")
    sys.exit(1)

  try:
    # socket
    if args.protocol == 'udp':
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    else:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((args.host, args.port))

    destination = (args.host, args.port)
    logging.info("Socket Initialized")
  except Exception as e:
    logging.error(f"While connecting to server: {e}")
    sys.exit(1)

  # start streaming
  while True:
    sendAudio()

  





