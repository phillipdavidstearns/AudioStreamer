import socket
import argparse
import signal
import pyaudio
import sys
import logging

# signal handler
def handler(signum, frame):
  global playStream, server_socket
  logging.info("Exiting the program")
  playStream.stop_stream()
  server_socket.close()
  sys.exit(0)

def recvData():
  global expectedSeqNum, playStream, silenceData, server_socket, connection

  logging.debug(f"Expecting Sequence #{expectedSeqNum}")

  if args.protocol == 'udp':
    data, address = server_socket.recvfrom(CHUNK * NUMCHUNKS * 2 + 2)
  else:
    data = connection.recv(CHUNK * NUMCHUNKS * 2 + 2)
    while len(data) < CHUNK * NUMCHUNKS * 2 + 2:
      data += connection.recv(CHUNK * NUMCHUNKS * 2 + 2 - len(data))

  sequenceNumber = int.from_bytes(data[:2], byteorder="little", signed=False)
  audioData = data[2:]

  if expectedSeqNum == sequenceNumber:
    # play
    logging.debug(f"Received Sequence #{sequenceNumber} ({len(data)} bytes)")
    playStream.write(audioData)

    expectedSeqNum = (expectedSeqNum + 1) % 65536
  else:
    logging.debug(f"Received Out of Sequence # {sequenceNumber} ({len(data)} bytes)")
    # play silence
    playStream.write(silenceData)

    if sequenceNumber > expectedSeqNum:
      # catch up
      expectedSeqNum = sequenceNumber + 1

if __name__ == '__main__':

  # signal handler
  signal.signal(signal.SIGINT, handler)

  # command line arguments
  parser=argparse.ArgumentParser(description="AudioStream server")
  parser.add_argument("--protocol", required=False, default='udp', choices=['udp', 'tcp'])
  parser.add_argument("--port", required=False, default=12345)
  parser.add_argument("--size", required=False, default=10, type=int, choices=range(10, 151, 10))
  parser.add_argument("--loglevel", required=False, default=20, type=int, choices=[0,10,20,30,40,50])
  args=parser.parse_args()

  logging.basicConfig(format='[AudioStream SERVER] - %(levelname)s | %(message)s', level=args.loglevel)

  logging.info(f"Protocol: {args.protocol.upper()}")
  logging.info(f"Port: {args.port}")
  logging.info(f"Size: {args.size} ms")

  # audio setup
  FORMAT = pyaudio.paInt16
  CHANNELS = 1
  RATE = 44100
  CHUNK = 441 # 10 ms
  NUMCHUNKS = int(args.size / 10)

  silence = 0
  silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS

  try:

    pyaudioObj = pyaudio.PyAudio()

    playStream = pyaudioObj.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      output=True,
      frames_per_buffer=CHUNK * NUMCHUNKS
    )

    logging.info("PyAudio Device Initialized")
  except Exception as e:
    logging.error(f"While inializing audio device: {e}")
    sys.exit(1)

  try:
    # socket
    if args.protocol == 'udp':
      server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      server_socket.bind(('', args.port))
    else:
      server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server_socket.bind(('', args.port))
      server_socket.listen()
      connection, source = server_socket.accept()

    logging.info("Socket Initialized")
  except Exception as e:
    logging.error(f"While initializing socket: {e}")
    sys.exit(1)

  expectedSeqNum = 0

  while True:
    recvData()
