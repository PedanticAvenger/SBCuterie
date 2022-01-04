#
# Hardware and overall function constants
#
DEBUG_STATUS = False
I2C_BUS = 7  # Define the system bus to use for I2C transactions, RaspPi is 1, RockPi is 7 for "default" bus
I2C_MUX_ADDR = 0x70  # I2C address for the I2C multiplexer to switch channels to talk to different components
RELAY_DEV_ADDRESS = 0x11  # I2C Address for relay module
RELAY_NUM = {
    "heating": 1,
    "cooling": 2,
    "humidifier": 3,
    "dehumidifier": 4,
}

# Defaults for constants we will want to overwrite from DB, relevant to conditions in chamber.
MAX_TEMP_SENSOR_DRIFT = 3
CURRENT_TEMP_MAX_OVERSHOOT = 2

MAX_HUMI_SENSOR_DRIFT = 6
CURRENT_HUMI_MAX_OVERSHOOT = 3
HUMIDITY_CONTROL = "YES"

"""
Constants to tune operation of the software, these set things like how hard
we can/can't work the compressor in the fridge, how long we should run the
humidifier on each request to increase humidity, etc.
These values would GENERALLY not vary batch to batch, but they might belong 
in the DB eventually to ease administration
"""
SLEEP_SECONDS = 30  # How long between runs through our control loop

COMPRESSOR_IDLE_TIME = 900  # wait number seconds before cycling cool
HEAT_IDLE_TIME = 1  # wait number seconds before cycling heat

HUMIDIFIER_DUTY = 4  # number of seconds to switch humidifier on each loop
HUMIDIFIER_IDLE_TIME = 60  # wait number seconds before cycling humidifier


AirPumpDuty = 120  # how long to run air pump.  Could move DB to allow tweaking.
AirPumpIdleTime = 7200  # off for how long.

# Circulation fan controls removed.  Assumption is that fan runs 100% and speed/airflow is tuned to appropriate levels

PANIC_HOT = 30  # exit if temp too high or too low, these values are set in C
PANIC_COLD = 4


# Location of the software watchdog file.
# Set the following variable to point to the appropriate path for where your script is running
# During development this is running in a venv so very local.
SOFTDOG_FILE = "PiCuterie.softdog"

# Email info to allow sending of Alerts via default channel.
# Setting defaults to gmail due to the odds.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # for TLS
SENDER_EMAIL = "my@gmail.com"
EMAIL_PASSWORD = "you be careful with this"
