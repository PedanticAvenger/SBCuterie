import os
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import controller.modules.const as CONST  # Operating Values that may need to be tweaked moved to separate file in includes.
from controller.modules.AHT20 import AHT20  # Lib for AHT20 sensors
import controller.modules.TCA9548A as TCA9548  # Lib for I2C MUX


def quorum_check(value_x, value_y, value_z, delta_max):
    """
    Quorum Checking function
    Requires 3 input values and a max allowed delta between sensors as args.
    Checks all 3 values against each other and max delta to determine if sensor has
    failed or is way out of agreement with the other two.
    Returns a "Return Code" and a value.
    Return Codes:
    0 - All sensors agree,
    1 - sensor x out of spec,
    2 - sensor y out of spec,
    3 - sensor z out of spec,
    4 - no sensors agree, you should error out/email/alarm/etc.
    5 - sensors agree in pairs but spread across all 3 exceeds delta
    """
    # Reset values
    agree_xy = False
    agree_xz = False
    agree_yz = False

    x_min = value_x - delta_max
    x_max = value_x + delta_max
    y_min = value_y - delta_max
    y_max = value_y + delta_max

    # Check for agreement between pairs
    if x_min <= value_y <= x_max:
        agree_xy = True
    if x_min <= value_z <= x_max:
        agree_xz = True
    if y_min <= value_z <= y_max:
        agree_yz = True

    # Evaluate if all sensors either disagree or agree
    if not (agree_xy) and not (agree_xz) and not (agree_yz):
        val = 0
        return_val = [4, val]
        return return_val  # Set this to return error code stating none of the sensors agree

    if agree_xy and agree_xz and agree_yz:
        val = (value_x + value_y + value_z) / 3
        val = round(val, 1)
        return_val = [0, val]
        return (
            return_val  # Set this to return all good code and average of all 3 sensors
        )

    # Catch edge case of agreement between two separate pairs but not the third.
    # For this case also return an average of all 3.
    if (
        (agree_xy and agree_yz and not agree_xz)
        or (agree_yz and agree_xz and not agree_xy)
        or (agree_xy and agree_xz and not agree_yz)
    ):
        val = (value_x + value_y + value_z) / 3
        val = round(val, 1)
        return_val = [5, val]
        return return_val  # Set this to return all large spread code and average of all 3 sensors

    # If we flow through all the previous checks, identify which sensor is out of line with quorum.
    if agree_xy and not agree_yz and not agree_xz:
        val = (value_x + value_y) / 2
        val = round(val, 1)
        return_val = [3, val]
        return return_val  # Set this to return one bad sensor code for sensor z and average of 2 remaining sensors

    if not agree_xy and agree_yz and not agree_xz:
        val = (value_y + value_z) / 2
        val = round(val, 1)
        return_val = [1, val]
        return return_val  # Set this to return one bad sensor code for sensor x and average of 2 remaining sensors

    if not agree_xy and not agree_yz and agree_xz:
        val = (value_x + value_z) / 2
        val = round(val, 1)
        return_val = [2, val]
        return return_val  # Set this to return one bad sensor code for sensor y and average of 2 remaining sensors


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


# Read Sensors
(
    last_sensor_read_time,
    read_temp_code,
    read_temp,
    read_hum_code,
    read_hum,
) = get_sensor_data()

print(
    "Temp Quorum is "
    + str(read_temp)
    + " degrees with code '"
    + str(read_temp_code)
    + "' at "
    + str(last_sensor_read_time)
    + "."
)
print(
    "Humidity Quorum is "
    + str(read_hum)
    + "% with code '"
    + str(read_hum_code)
    + "' at "
    + str(last_sensor_read_time)
    + "."
)
