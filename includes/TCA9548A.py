"""
Module to handle TCA9548A I2C Multiplexer via SMBus calls
requires SMBus2 to be installed
"""

from smbus2 import SMBus
import time
import sys

# Define the command to set each channel, 1 through 8
mux_channel_array = [
    0b00000001,
    0b00000010,
    0b00000100,
    0b00001000,
    0b00010000,
    0b00100000,
    0b01000000,
    0b10000000,
]


def i2c_mux_channel(
    I2CBus=1, multiplexer_addr=0x70, i2c_channel_setup=1, debug_status=False
):
    if isinstance(i2c_channel_setup, int):
        bus = SMBus(I2CBus)
        bus.write_byte(multiplexer_addr, mux_channel_array[i2c_channel_setup])
        time.sleep(0.01)
        if debug_status:
            print("TCA9548A I2C channel status:", bin(bus.read_byte(multiplexer_addr)))
    else:
        print("Channel specification must be integer.")
