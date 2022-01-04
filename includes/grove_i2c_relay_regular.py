"""
 Seeed Studio Grove - 4/8-Channel I2C SPDT/SSR Relay Board
 Python Module

 by Raymond Richmond

 Modified from code by John M. Wargo
 (https://github.com/johnwargo/seeed-studio-relay-v2)
 to support Python on linux SBCs and this specific relay board family.
 _regular version is for a "typical" python sbc environment i.e.
 not requireing circuitpython but leveraging SMBus calls
"""

from smbus2 import SMBus
import time

# Globals for the object
CMD_CHANNEL_CONTROL = 0x10
CMD_SAVE_I2C_ADDR = 0x11
CMD_READ_I2C_ADDR = 0x12
CMD_READ_FIRMWARE_VER = 0x13
CHANNEL_BIT = {
    "1": 0b00000001,
    "2": 0b00000010,
    "3": 0b00000100,
    "4": 0b00001000,
    "5": 0b00010000,
    "6": 0b00100000,
    "7": 0b01000000,
    "8": 0b10000000,
}

# Instantiate the class
class RELAY:
    def __init__(
        self,
        i2cbus=1,
        device_address=0x11,
        num_relays=4,
        debug_action=False,
    ):

        self.I2CBusNum = i2cbus
        self.DEVICE_ADDRESS = device_address
        self.NUM_RELAY_PORTS = num_relays  # 4 or 8 are really the only allowed numbers
        self.channel_state = 0x00

        print("Initializing relay board at 0x{:x}".format(self.DEVICE_ADDRESS))

        if debug_action:
            print("Enabling action_output mode")

        self.debug = debug_action

        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_byte_data(
                self.DEVICE_ADDRESS,
                CMD_CHANNEL_CONTROL,
                self.channel_state,
            )

    # If you have address conflicts on your I2C bus you can use this function to reset the relay module address
    # Remember to change your address in your code for future instantiations of this object

    def change_i2c_address(self, old_address, new_address):
        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_i2c_byte_data(
                self.DEVICE_ADDRESS,
                CMD_SAVE_I2C_ADDR,
                new_address,
            )
            self.DEVICE_ADDRESS = new_address
        return True

    # This function is for when your code keeps track of the full state of all relays and you just want to toggle directly.
    def channel_control(self, state):
        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_i2c_byte_data(
                self.DEVICE_ADDRESS,
                CMD_CHANNEL_CONTROL,
                state,
            )
            self.channel_state = state
            time.sleep(
                0.05
            )  # Wait 50ms for activation, probably not needed but fine anyways
        return True

    # Turn on a single channel
    def channel_on(self, relay_num):
        if isinstance(relay_num, int):  # Check that not getting garbage
            if 0 < relay_num <= self.NUM_RELAY_PORTS:  # check for valid relay number
                if self.debug:
                    print("Turning relay {} on".format(relay_num))
                self.channel_state |= 1 << (relay_num - 1)
                with SMBus(self.I2CBusNum) as i2c_bus:
                    i2c_bus.write_byte_data(
                        self.DEVICE_ADDRESS,
                        CMD_CHANNEL_CONTROL,
                        self.channel_state,
                    )
                return True
            else:
                print("Invalid relay: #{}".format(relay_num))
                return False
        else:
            print("Relay number must be an Integer value")
            return False

    # Turn off a single channel
    def channel_off(self, relay_num):
        if isinstance(relay_num, int):  # Check that not getting garbage
            if 0 < relay_num <= self.NUM_RELAY_PORTS:  # check for valid relay number
                if self.debug:
                    print("Turning relay {} off".format(relay_num))
                self.channel_state &= ~(1 << (relay_num - 1))
                with SMBus(self.I2CBusNum) as i2c_bus:
                    i2c_bus.write_byte_data(
                        self.DEVICE_ADDRESS,
                        CMD_CHANNEL_CONTROL,
                        self.channel_state,
                    )
                return True
            else:
                print("Invalid relay: #{}".format(relay_num))
                return False
        else:
            print("Relay number must be an Integer value")
            return False

    # Turn on all channels at once.
    def all_channel_on(self):
        if self.debug:
            print("Turning all relays ON")
        self.channel_state |= 0xF << 0
        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_byte_data(
                self.DEVICE_ADDRESS,
                CMD_CHANNEL_CONTROL,
                int(self.channel_state),
            )
        return True

    # Turn off all channels at once.
    def all_channel_off(self):
        if self.debug:
            print("Turning all relays OFF")
        self.channel_state &= ~(0xF << 0)
        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_byte_data(
                self.DEVICE_ADDRESS,
                CMD_CHANNEL_CONTROL,
                int(self.channel_state),
            )
        return True

    # Toggle state for a single relay.  On -> Off, Off -> On
    def toggle_channel(self, relay_num):
        if self.debug:
            print("Toggling relay:", relay_num)
        if self.get_port_status(relay_num):
            # it's on, so turn it off
            self.channel_off(relay_num)
        else:
            # it's off, so turn it on
            self.channel_on(relay_num)

    # Process the current relay board state and return status bit for desired relay.
    def get_channel_status(self, relay_num):
        output = str(relay_num)
        status = self.channel_state
        status = bin(int(status))
        status >> bin(CHANNEL_BIT[output]) & 1
        return status

    # Process the current relay board state and print out status for desired relay.
    def print_channel_status(self, relay_num):
        output = str(relay_num)
        status = self.channel_state
        if status & CHANNEL_BIT[output] > 0:
            output += ": On  "
        else:
            output += ": Off "
        print("Relay {}".format(relay_num, output))

    # Process the current relay board state and print out status for all relays.
    def print_status_all(self):
        output = "| "
        for x in range(1, self.NUM_RELAY_PORTS + 1):
            status = self.channel_state
            output += str(x)
            if status & CHANNEL_BIT[str(x)] > 0:
                output += ": On  | "
            else:
                output += ": Off | "
        print("Relay status: {}".format(output))

    # Query the board and get the current firmware version.
    # 99% of the time people won't need this I suspect but copied as it was part of Arduino ref lib
    def get_firmware_version(self):
        with SMBus(self.I2CBusNum) as i2c_bus:
            i2c_bus.write_byte_data(self.DEVICE_ADDRESS, 0, CMD_READ_FIRMWARE_VER)
            ver = i2c_bus.read_byte_data(self.DEVICE_ADDRESS, 0)
        return ver
