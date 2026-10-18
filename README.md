# AudioStreamer

Simple audio streaming application using TCP in python

The client and server code for the audio streaming application utilizes a network programming approach with asyncio to transmit audio data between a client and a server:

## Architecture Overview

This audio streaming application is designed around a client-server architecture that enables 
real-time audio streaming over the network. The application supports TCP protocols via asyncio for reliable data transmission at the cost of latency.

## Server

Module Dependencies: Uses the asyncio, argparse, signal, pyaudio, python-decouple, logging and sys modules.

### Functionality:

The server initializes a TCP socket connection on a specified port and listens for incoming audio streams from the client. It uses the pyaudio library to play the incoming audio stream in real-time using a callback. A signal handler is implemented to gracefully shut down the server on receiving a SIGINT signal, ensuring that resources are properly released.

## Client

Module Dependencies: Similar to the server, it utilizes the asyncio, argparse, signal, pyaudio, python-decouple, logging and sys.

## Buffer

A class that implements a FIFO buffer used for audio data. Currently used by both Client and Server.

### Functionality:

The client captures audio input from a microphone using the pyaudio library via callback. Audio data is then sent to the server over an asyncio managed connection using TCP. Implements a signal handler to intercept SIGINT signals for a graceful shutdown, closing the socket and releasing resources properly.

## Key Features

* Asyncio architecture allows for client and server to be started independently. Connections are made and restored when lost automatically.
* Real-Time Audio Streaming: Leverages the pyaudio library for capturing and playing audio in 
real-time, facilitating live audio streaming over the network.
* Graceful Shutdown: Both the client and server are equipped with signal handlers to manage
unexpected exits, ensuring that resources are not left hanging.

## Installation

### Raspberry Pi
  
* Install dependencies for compiling pyaudio on raspberry pi: `sudo apt-get update && sudo apt-get install python3-dev portaudio19-dev`

## Usage

Both the client and server scripts accept command-line arguments to specify the protocol (--protocol with options udp or tcp).
The server must be started before the client and set to listen on a specific port.
The client then connects to the server's IP address and port, beginning the audio stream.
