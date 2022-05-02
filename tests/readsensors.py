import includes.const as CONST  # Operating Values that may need to be tweaked moved to separate file in includes.
from includes.AHT20 import AHT20  # Lib for AHT20 sensors
import includes.TCA9548A as TCA9548  # Lib for I2C MUX


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
        i2c_channel_setup=CONST.ATHX_MUX_ADDR,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_a = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_a_hum = sensor_a.get_humidity
    sensor_a_temp = sensor_a.get_temperature

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.ATHY_MUX_ADDR,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_b = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_b_hum = sensor_b.get_humidity
    sensor_b_temp = sensor_b.get_temperature

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=CONST.ATHZ_MUX_ADDR,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_c = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_c_hum = sensor_c.get_humidity
    sensor_c_temp = sensor_c.get_temperature

    return (
        sensor_a_temp,
        sensor_b_temp,
        sensor_c_temp,
        sensor_a_hum,
        sensor_b_hum,
        sensor_c_hum,
    )


# Read Sensors
(x_temp, y_temp, z_temp, x_hum, y_hum, z_hum) = get_sensor_data()
print("X/Y/Z_temp= ", x_temp, y_temp, z_temp)
print("X/Y/Z_hum= ", x_hum, y_hum, z_hum)
