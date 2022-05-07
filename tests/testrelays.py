import os
import sys
import time
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import controller.modules.const as CONST  # Operating Values that may need to be tweaked moved to separate file in includes.
from controller.modules.AHT20 import AHT20  # Lib for AHT20 sensors
import controller.modules.TCA9548A as TCA9548  # Lib for I2C MUX
from controller.modules.grove_i2c_relay_regular import RELAY  # Lib for I2C relays


def get_sensor_data():
    """
    Get Sensor Data
    In this block we will read 3 temp/humidity sensors, call quorum
    function and report readings and/or error conditions.  We require the MUX
    lane (1/2/3/4/5/6/7/8) for sensors A/B/C set in the globals as well as max
    drift between two sensors beyond which we consider a sensor to be in error.
    Select the appropriate mux port for each AHT20 sensor then read the values,
    check for quorum, return values.
    DEV NOTE: Remember to set handling for exceptional errors.
    """
    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.AHTX_MUX_CHAN,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_a = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_a_hum = sensor_a.get_humidity()
    sensor_a_temp = sensor_a.get_temperature()

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.AHTY_MUX_CHAN,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_b = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_b_hum = sensor_b.get_humidity()
    sensor_b_temp = sensor_b.get_temperature()

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.AHTZ_MUX_CHAN,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_c = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_c_hum = sensor_c.get_humidity()
    sensor_c_temp = sensor_c.get_temperature()

    last_sensor_read_time = datetime.datetime.now()

    temp_check = quorum_check(
        sensor_a_temp, sensor_b_temp, sensor_c_temp, CONST.MAX_TEMP_SENSOR_DRIFT
    )
    hum_check = quorum_check(
        sensor_a_hum, sensor_b_hum, sensor_c_hum, CONST.MAX_HUMI_SENSOR_DRIFT
    )

    if temp_check[0] == 0:
        # All sensors agree
        return_temp = temp_check[1]
        return_temp_code = "Good"
    if temp_check[0] == 1:
        # Sensor X Bad
        return_temp = temp_check[1]
        return_temp_code = "Sensor X Disagrees"
        sys.stderr.write("Temperature Sensor X disagrees with other two.")
    if temp_check[0] == 2:
        # Sensor Y Bad
        return_temp = temp_check[1]
        return_temp_code = "Sensor Y Disagrees"
        sys.stderr.write("Temperature Sensor Y disagrees with other two.")
    if temp_check[0] == 3:
        # Sensor Z Bad
        return_temp = temp_check[1]
        return_temp_code = "Sensor Z Disagrees"
        sys.stderr.write("Temperature Sensor Z disagrees with other two.")
    if temp_check[0] == 4:
        # No sensors agree
        return_temp = 0
        return_temp_code = "No Sensors Agree"
        sys.stderr.write("None of the Termperature Sensors agree.")
    if temp_check[0] == 5:
        # 2 pair agreement, spread > MAX_DRIFT but average usable
        return_temp = temp_check[1]
        return_temp_code = "Large Spread"
        sys.stderr.write(
            "Range Across All Temperature Sensors exceeds max delta but pairs good."
        )

    if hum_check[0] == 0:
        # All sensors agree
        return_hum = hum_check[1]
        return_hum_code = "Good"
    if hum_check[0] == 1:
        # Sensor X Bad
        return_hum = hum_check[1]
        return_hum_code = "Sensor X Disagrees"
        sys.stderr.write("Humidity Sensor X disagrees with other two.")
    if hum_check[0] == 2:
        # Sensor Y Bad
        return_hum = hum_check[1]
        return_hum_code = "Sensor Y Disagrees"
        sys.stderr.write("Humidity Sensor Y disagrees with other two.")
    if hum_check[0] == 3:
        # Sensor Z Bad
        return_hum = hum_check[1]
        return_hum_code = "Sensor Z Disagrees"
        sys.stderr.write("Humidity Sensor Z disagrees with other two.")
    if hum_check[0] == 4:
        # No sensors agree
        return_hum = 0
        return_hum_code = "No Sensors Agree"
        sys.stderr.write("None of the Humidity Sensors agree.")
    if hum_check[0] == 5:
        # 2 pair agreement, spread > MAX_DRIFT but average usable
        return_hum = hum_check[1]
        return_hum_code = "Large Spread"
        sys.stderr.write(
            "Range Across All Humidity Sensors exceeds max delta but pairs good."
        )

    return (
        last_sensor_read_time,
        return_temp_code,
        return_temp,
        return_hum_code,
        return_hum,
    )


def set_device_status(device, setting):
    """
    This function sets the relay status for the appropriate device.
    Uses globals for the appropriate I2C addresses and values to
    reference the appropriate relay.
    Devices:
        heating
        cooling
        humidifier
        dehumidifier
        *air (This one may live off a GPIO pin but is sidelined until I decide if I actually need it)

    Settings:
        ON
        OFF
    """
    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.OUT1_MUX_CHAN,  # Assume by default the relays are plugged into the first output port
        debug_status=CONST.DEBUG_STATUS,
    )
    relay = RELAY(
        i2cbus=CONST.I2C_BUS,
        device_address=CONST.RELAY_DEV_ADDRESS,
        num_relays=4,
        debug_action=CONST.DEBUG_STATUS,
    )

    if setting == "ON":
        relay.channel_on(CONST.RELAY_NUM[device])

    if setting == "OFF":
        relay.channel_off(CONST.RELAY_NUM[device])

    if CONST.DEBUG_STATUS:
        print("Set " + device + " status to " + setting + " at " + time.strftime("%c"))

    return time.time()


# Toggle Through Relays
time1 = set_device_status("heating", "ON")
time.sleep(3)
print(time1)
time1 = set_device_status("heating", "OFF")
time.sleep(1)
print(time1)
time1 = set_device_status("cooling", "ON")
time.sleep(3)
print(time1)
time1 = set_device_status("cooling", "OFF")
time.sleep(1)
print(time1)
time1 = set_device_status("humidifier", "ON")
time.sleep(3)
print(time1)
time1 = set_device_status("humidifier", "OFF")
time.sleep(1)
print(time1)
time1 = set_device_status("dehumidifier", "ON")
time.sleep(3)
print(time1)
time1 = set_device_status("dehumidifier", "OFF")
time.sleep(1)
print(time1)
