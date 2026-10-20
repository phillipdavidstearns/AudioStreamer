#================================================================
import logging

#================================================================
# Behaves like FIFO

class Buffer:

  #----------------------------------------------------------------

  def __init__(self, size_limit=7056000, zero_pad=True):
    self.buffer = bytearray()
    self.size_limit = size_limit
    self.zero_pad = zero_pad

  #----------------------------------------------------------------

  def clear(self):
    self.buffer = bytearray()

  #----------------------------------------------------------------

  def get(self, qty_bytes):
    
    # grab a slice of the buffer
    data = self.buffer[:qty_bytes]

    # FIFO slicing
    self.buffer = self.buffer[qty_bytes:]
    
    if self.zero_pad and qty_bytes > len(data):
      data += bytes([0]) * (qty_bytes - len(data))
    
    return data

  #----------------------------------------------------------------

  def get_all(self):
    data = self.buffer.copy()
    self.buffer.clear()
    return data

  #----------------------------------------------------------------

  def size(self):
    return len(self.buffer)

  #----------------------------------------------------------------

  def put(self, data):
    if self.size() < self.size_limit:
      self.buffer.extend(data)
