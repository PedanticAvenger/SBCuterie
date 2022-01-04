"""                                                                
           SBCuterie (Evolved from PorkPi by HJBCT44)
                                                 
                               -PedanticAvenger  
                               -HJBCT44 (et al)  

python 3 operating target, SMBus2 I2C bus controls.
Google Sheets integration removed for first iteration, replaced with local SQLite.
Added MIT license
"""

import os

# import json
import sys
import time
import datetime
import smtplib, ssl, email.message  # Keep this in here and add email functions for various notifications.
import sqlite3

# Local project file imports
import includes.const as CONST  # Operating Values that may need to be tweaked moved to separate file in includes.
from includes.AHT20 import AHT20  # Lib for AHT20 sensors
from includes.grove_i2c_relay_regular import RELAY  # Lib for I2C relays
import includes.TCA9548A as TCA9548  # Lib for I2C MUX

#
# Functions
#


def touch(fname):
    """
    Update the timestamp on the watchdog file, which is watched by an external shell script.
    """
    if os.path.exists(fname):
        os.utime(fname, None)
    else:
        open(fname, "a").close()


def load_db_values(ID):
    """
    This function is called at script initialization and loads operating values
    from a local SQLite DB and makes them available throughout the script.
    Yes this isn't really the optimal case for a SQL db but it allows for future
    enhancements to selecting profiles, etc. easily.

    Values in main call would include:
        ProfileLabel # What is the Label for this group of settings?
        CurrentTempSetpoint # Current target for temp (Stored as REAL to handle F/C conversions better)
        CurrentTempMaxOvershoot # How much can we run over/under our set point before we apply compensation? (Stored as REAL)
        ControlTemperature # Are we controlling temperature? (YES/NO)
        CurrentHumiditySetpoint # Current target for humidity (Stored as REAL)
        CurrentHumidityMaxOvershoot # How much can we run over/under our set point before we apply compensation?
        ControlHumidity # Are we controlling Humidity? (YES/NO)
        AirPumpDuty # How long will the air pump run when we trigger it (seconds as INT)
        AirPumpIdleTime # How long will the air pump sit idle between cycles (seconds as INT)
        LogServerStatus # Will we use a log server (ELK/Splunk/syslog/etc.) for our output? (YES/NO)
        CommandEmailAddress # Email account to check for control commands. (TEXT)
        NotificationEmailAddress # What is the notification email for alerting/etc. (TEXT)
        ReportingConfig # Are we going to report to a GoogleSheet? (YES/NO)
        GoogleSheetID  # Not yet - For the current google spreadsheet we are logging to and "value" is a key in another table for the sheet config
        ScheduleStatus # Are we running a scheduled curing profile or static targets?
        ScheduleID # What Schedule are we running?
    """
    setting_id = ID
    conn = sqlite3.connect("SBCuterieDB.db")
    query = conn.execute(
        "SELECT ProfileLabel,AirPumpDuty,AirPumpIdleTime,LogServerStatus,NotificationEmail,ReportingConfig,ScheduleStatus,ScheduleID from CTRLSETTING WHERE ID = ?",
        (setting_id),
    )
    query2 = conn.execute(
        "SELECT CurrentTempSetPoint,CurrentTempMaxOvershoot,CurrentHumiditySetpoint,CurrentHumidityMaxOvershoot,ControlHumidity from ENVSETTING WHERE ID = ?",
        (setting_id),
    )
    conn.close()
    return {
        "ProfileLabel": query[0],
        "AirPumpDuty": query[1],
        "AirPumpIdleTime": query[2],
        "LogServerStatus": query[3],
        "NotificationEmail": query[4],
        "ReportingConfig": query[5],
        "ScheduleStatus": query[6],
        "ScheduleID": query[7],
        "CurrentTempSetPoint": query2[0],
        "CurrentTempMaxOvershoot": query2[1],
        "CurrentHumiditySetpoint": query2[2],
        "CurrentHumidityMaxOvershoot": query2[3],
        "ControlHumidity": query2[4],
    }


def quorum_check(value_x, value_y, value_z, delta_max):
    """
    Quorum Checking function
    Requires 3 input values and a max allowed delta between sensors as args.
    Checks all 3 values against each other and max delta to determine if sensor has
    failed or is way out of agreement with the other two.
    Returns a "Return Code" and a value.
    Return Codes:
    0 - All sensors agree,
    1 - sensor x bad,
    2 - sensor y bad
    3 - sensor z bad,
    4 - no sensors agree, you should error out/email/alarm/etc.
    5 - sensors agree in pairs but spread across all 3 exceeds delta
    """
    # Reset values
    agree_xy = False
    agree_xz = False
    agree_yz = False

    # Check for agreement between pairs
    if (value_x - delta_max) <= value_y <= (value_x + delta_max):
        agree_xy = True
    if (value_x - delta_max) <= value_z <= (value_x + delta_max):
        agree_xz = True
    if (value_y - delta_max) <= value_z <= (value_y + delta_max):
        agree_yz = True

    # Evaluate if all sensors either disagree or agree
    if ~agree_xy and ~agree_xz and ~agree_yz:
        val = 0
        return_val = [4, val]
        return False  # Set this to return error code stating none of the sensors agree

    if agree_xy and agree_xz and agree_yz:
        val = (value_x + value_y + value_z) / 3
        return_val = [0, val]
        return (
            return_val  # Set this to return all good code and average of all 3 sensors
        )

    # Catch edge case of agreement between two separate pairs but not the third.
    # For this case also return an average of all 3.
    if (
        (agree_xy and agree_yz and ~agree_xz)
        or (agree_yz and agree_xz and ~agree_xy)
        or (agree_xy and agree_xz and ~agree_yz)
    ):
        val = (value_x + value_y + value_z) / 3
        return_val = [5, val]
        return return_val  # Set this to return all large spread code and average of all 3 sensors

    # If we flow through all the previous checks, identify which sensor is out of line with quorum.
    if agree_xy and ~agree_yz and ~agree_xz:
        val = (value_x + value_y) / 2
        return_val = [3, val]
        return return_val  # Set this to return one bad sensor code for sensor z and average of 2 remaining sensors

    if ~agree_xy and agree_yz and ~agree_xz:
        val = (value_y + value_z) / 2
        return_val = [1, val]
        return return_val  # Set this to return one bad sensor code for sensor x and average of 2 remaining sensors

    if ~agree_xy and ~agree_yz and agree_xz:
        val = (value_x + value_z) / 2
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
        i2c_channel_setup=1,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_a = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_a_hum = sensor_a.get_humidity
    sensor_a_temp = sensor_a.get_temperature

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=1,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_b = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_b_hum = sensor_b.get_humidity
    sensor_b_temp = sensor_b.get_temperature

    TCA9548.i2c_mux_channel(
        I2CBus=CONST.I2C_BUS,
        multiplexer_addr=CONST.I2C_MUX_ADDR,
        i2c_channel_setup=1,
        debug_status=CONST.DEBUG_STATUS,
    )
    sensor_c = AHT20(I2CBusNum=CONST.I2C_BUS)
    sensor_c_hum = sensor_c.get_humidity
    sensor_c_temp = sensor_c.get_temperature

    last_sensor_read_time = datetime.datetime.now()

    temp_check = quorum_check(
        sensor_a_temp, sensor_b_temp, sensor_c_temp, CONST.MAX_TEMP_SENSOR_DRIFT
    )
    hum_check = quorum_check(
        sensor_a_hum, sensor_b_hum, sensor_c_hum, CONST.MAX_HUMI_SENSOR_DRIFT
    )

    if temp_check[1] == 0:
        # All sensors agree
        return_temp = temp_check[2]
        return_temp_code = "Good"
    if temp_check[1] == 1:
        # Sensor X Bad
        return_temp = temp_check[2]
        return_temp_code = "Sensor X Disagrees"
        sys.stderr.write("Temperature Sensor X disagrees with other two.")
    if temp_check[1] == 2:
        # Sensor Y Bad
        return_temp = temp_check[2]
        return_temp_code = "Sensor Y Disagrees"
        sys.stderr.write("Temperature Sensor Y disagrees with other two.")
    if temp_check[1] == 3:
        # Sensor Z Bad
        return_temp = temp_check[2]
        return_temp_code = "Sensor Z Disagrees"
        sys.stderr.write("Temperature Sensor Z disagrees with other two.")
    if temp_check[1] == 4:
        # No sensors agree
        return_temp = 0
        return_temp_code = "No Sensors Agree"
        sys.stderr.write("None of the Termperature Sensors agree.")
    if temp_check[1] == 5:
        # 2 pair agreement, spread > MAX_DRIFT but average usable
        return_temp = temp_check[2]
        return_temp_code = "Large Spread"
        sys.stderr.write(
            "Range Across All Temperature Sensors exceeds max delta but pairs good."
        )

    if hum_check[1] == 0:
        # All sensors agree
        return_hum = hum_check[2]
        return_hum_code = "Good"
    if hum_check[1] == 1:
        # Sensor X Bad
        return_hum = hum_check[2]
        return_hum_code = "Sensor X Disagrees"
        sys.stderr.write("Humidity Sensor X disagrees with other two.")
    if hum_check[1] == 2:
        # Sensor Y Bad
        return_hum = hum_check[2]
        return_hum_code = "Sensor Y Disagrees"
        sys.stderr.write("Humidity Sensor Y disagrees with other two.")
    if hum_check[1] == 3:
        # Sensor Z Bad
        return_hum = hum_check[2]
        return_hum_code = "Sensor Z Disagrees"
        sys.stderr.write("Humidity Sensor Z disagrees with other two.")
    if hum_check[1] == 4:
        # No sensors agree
        return_hum = 0
        return_hum_code = "No Sensors Agree"
        sys.stderr.write("None of the Humidity Sensors agree.")
    if hum_check[1] == 5:
        # 2 pair agreement, spread > MAX_DRIFT but average usable
        return_hum = hum_check[2]
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
        i2c_channel_setup=8,  # Assume by default the relays are plugged into the last port
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


def write_logs(temperature, humidity, event):
    """
    Support for future gsheets logging, syslog, whatever will get added here, alerts is send_alert function.
    Default always writes to local SQLite DB, others are potential extras.
    """
    conn = sqlite3.connect("SBCuterieDB.db")
    sql1 = """ INSERT into ENVIROLOG (Time, Temperature, Humidity) VALUES (?,?,?) """
    sql2 = """ INSERT into EVENTLOG (Time, Event) VALUES (?,?) """
    ct = datetime.now()
    timestamp = datetime.timestamp(ct)
    conn.execute(sql1, (timestamp, temperature, humidity))
    conn.execute(sql2, (timestamp, event))
    conn.close()


def send_alert(subject, body):
    """
    Function to send alerts via various means.
    Email as default but future additional options can be added here
    """
    msg = email.message.Message()
    msg["From"] = CONST.SENDER_EMAIL
    msg["To"] = NotificationEmail
    msg["Subject"] = subject
    msg.set_payload(body)

    context = ssl.create_default_context()
    try:
        server = smtplib.SMTP(CONST.SMTP_SERVER, CONST.SMTP_PORT)
        server.starttls(context=context)  # Secure the connection
        server.login(CONST.SENDER_EMAIL, CONST.EMAIL_PASSWORD)
        server.sendmail(CONST.SENDER_EMAIL, NotificationEmail, msg.as_string)
    except Exception as e:
        # Print any error messages to stderr
        sys.stderr.write(e)
    finally:
        server.quit()


# #######################################################################################
#     Main loop
# #######################################################################################

# only allow one instance
try:
    import socket

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Create an abstract socket, by prefixing it with null.
    s.bind("\0postconnect_gateway_notify_lock")
except socket.error as e:
    error_code = e.args[0]
    error_string = e.args[1]
    print("Process already running (%d:%s ). Exiting" % (error_code, error_string))
    send_alert("Picuterie Startup failed, already running", error_string)
    sys.exit(0)

# OK, Start up
current_time_this_cure = datetime.datetime.now()
print("Starting SBCuterie at " + time.strftime("%c"))
send_alert("Picuterie Startup", "System startup triggered at" + time.strftime("%c"))

# Ensure everything is OFF
last_cool_time = set_device_status("cooling", "OFF")
last_heat_time = set_device_status("heating", "OFF")
last_humid_time = set_device_status("humidifier", "OFF")
last_dehumid_time = set_device_status("dehumidifier", "OFF")
# last_air_pump_off_time = set_device_status("air", "OFF")
# last_air_pump_on_time = last_air_pump_off_time
cool_status = "OFF"
heat_status = "OFF"
humidifier_status = "OFF"
dehumidifier_status = "OFF"
# air_pump_status = "OFF"

# Read Initial Data
# In a basic setup system will only be using one batch of settings at a time.
# This should be replaced with a look into the DB and pull out the active settings.
# Until then, we will load set #1.
results = load_db_values(1)
ProfileLabel = results["ProfileLabel"]
CurrentTempSetPoint = results["CurrentTempSetPoint"]
CurrentTempMaxOvershoot = results["CurrentTempMaxOvershoot"]
CurrentHumiditySetpoint = results["CurrentHumiditySetpoint"]
CurrentHumidityMaxOvershoot = results["CurrentHumidityMaxOvershoot"]
ControlHumidity = results["ControlHumidity"]
# AirPumpDuty = results["AirPumpDuty"]
# AirPumpIdleTime = results["AirPumpIdleTime"]
LogServerStatus = results["LogServerStatus"]
NotificationEmail = results["NotificationEmail"]
ReportingConfig = results["ReportingConfig"]
ScheduleStatus = results["ScheduleStatus"]
ScheduleID = results["ScheduleID"]

last_refresh = time.time()

# Read Sensors
(
    last_sensor_read_time,
    temp_quorum_code,
    chamber_temperature,
    humidity_quorum_code,
    chamber_humidity,
) = get_sensor_data()

last_chamber_temperature = chamber_temperature
last_chamber_humidity = chamber_humidity

# Write our first set of values into the DB.
event = "Picuterie Startup"
write_logs(chamber_temperature, chamber_humidity, event)

state_change = 1  # make sure status gets written

# Main control loop the below state table is identical for humidity
#
# 		Heat delta to cool	-----------------------------		Turn Cooler On
# 		Temp error upper	------------  	Turn Heater Off
# 		Temp Setpoint 		------------<<
# 		Temp error lower	------------  	Turn Cooler Off
# 		Cool delta to Heat	-----------------------------		Turn Heater On
#

last_uptime = time.time()

print("Main")

while True:
    try:

        # Pat the dog
        touch(CONST.SOFTDOG_FILE)

        current_uptime = datetime.timedelta(seconds=int(time.time() - last_uptime))

        # Insert a query to log the uptime via UPDATE query to approprite table"

        # Do we need to refresh settings?
        # Do this once every 30 minutes from the DB, this implies that schedules can have a resolution no finer than 30 min.
        if (time.time() - last_refresh) > 1800:
            # remember to sub future variable in for the "1" below
            results = load_db_values(1)
            ProfileLabel = results["ProfileLabel"]
            CurrentTempSetPoint = results["CurrentTempSetPoint"]
            CurrentTempMaxOvershoot = results["CurrentTempMaxOvershoot"]
            CurrentHumiditySetpoint = results["CurrentHumiditySetpoint"]
            CurrentHumidityMaxOvershoot = results["CurrentHumidityMaxOvershoot"]
            ControlHumidity = results["ControlHumidity"]
            # AirPumpDuty = results["AirPumpDuty"]
            # AirPumpIdleTime = results["AirPumpIdleTime"]
            LogServerStatus = results["LogServerStatus"]
            NotificationEmail = results["NotificationEmail"]
            ReportingConfig = results["ReportingConfig"]
            ScheduleStatus = results["ScheduleStatus"]
            ScheduleID = results["ScheduleID"]
            last_refresh = time.time()

        # Read Sensors
        (
            last_sensor_read_time,
            temp_quorum_code,
            chamber_temperature,
            humidity_quorum_code,
            chamber_humidity,
        ) = get_sensor_data()

        # Check for quorum events in temp or humidity.
        if (temp_quorum_code != "Good") OR (humidity_quorum_code != "Good"):
            state_change = 1

        # Check for PANIC condition
        if (
            chamber_temperature > CONST.PANIC_HOT
            or chamber_temperature < CONST.PANIC_COLD
        ):

            time.sleep(10)

            (
                last_sensor_read_time,
                chamber_temperature,
                chamber_humidity,
            ) = get_sensor_data()

            if (
                chamber_temperature > CONST.PANIC_HOT
                or chamber_temperature < CONST.PANIC_COLD
            ):

                print("Temperature Panic : ", chamber_temperature)
                send_alert(
                    "Picuterie Temperature Panic",
                    "Chamber TEMP at" + chamber_temperature,
                )
                write_logs(
                    chamber_temperature,
                    chamber_humidity,
                    "Temperature Panic - Rebooting",
                )

                sys.stderr.write("Temperature Panic - rebooting\n")
                sys.stderr.flush()

                # Set all devices to off.
                last_cool_time = set_device_status("cooling", "OFF")
                last_heat_time = set_device_status("heating", "OFF")
                last_humid_time = set_device_status("humidifier", "OFF")
                last_humid_time = set_device_status("dehumidifier", "OFF")
                # last_air_pump_off_time = set_device_status("air", "OFF")
                # Shutdown and exit
                sys.exit(0)

        """
        # Commented this out until I get the air pump situation figured out
        # Cycle the air pump
        if air_pump_status == "OFF":
            if time.time() - last_air_pump_off_time > AirPumpIdleTime:
                last_air_pump_on_time = set_device_status("air", "ON")
                air_pump_status = "ON"
                state_change = 1

                if AirPumpDuty < SLEEP_SECONDS:  # allow for short fresh air duties
                    print("Wait for air pump...", AirPumpDuty, AirPumpIdleTime)
                    time.sleep(float(AirPumpDuty))

        if air_pump_status == "ON":
            if time.time() - last_air_pump_on_time > AirPumpDuty:
                last_air_pump_off_time = set_device_status("air", "OFF")
                air_pump_status = "OFF"
                state_change = 1
        """
        # #########################
        # TEMPERATURE CONTROL LOGIC
        # #########################

        if chamber_temperature >= (
            CurrentTempSetPoint + CurrentTempMaxOvershoot
        ):  # Heat setpoint + acceptable error exceeded - mainly to avoid overshoot

            # Turn heat off, only if not in dehumidify cycle
            if heat_status == "ON" and dehumidifier_status == "OFF":
                last_heat_time = set_device_status("heating", "OFF")
                heat_status = "OFF"
                state_change = 1

            if (
                chamber_temperature >= CurrentTempSetPoint + CurrentTempMaxOvershoot
            ):  # Heat setpoint significantly exceeded so active cool
                # Turn cooler on

                last_heat_time = set_device_status("heating", "OFF")
                heat_status = "OFF"

                if (
                    time.time() - last_cool_time > CONST.COMPRESSOR_IDLE_TIME
                ) and cool_status == "OFF":
                    last_cool_time = set_device_status("cooling", "ON")
                    cool_status = "ON"
                    state_change = 1

        if (
            chamber_temperature <= (CurrentTempSetPoint - CurrentTempMaxOvershoot)
            and chamber_temperature > CurrentTempSetPoint - CurrentTempMaxOvershoot
        ):
            # Heat setpoint - acceptable error exceeded .. mainly to avoid overshoot
            # but allow to drift down a little if dehumidifier is on
            if dehumidifier_status == "OFF":

                if cool_status == "ON":

                    last_cool_time = set_device_status("cooling", "OFF")
                    cool_status = "OFF"
                    state_change = 1

            if dehumidifier_status == "ON" and heat_status == "OFF":

                last_heat_time = set_device_status("heating", "ON")
                heat_status = "ON"

        if (
            chamber_temperature <= CurrentTempSetPoint - CurrentTempMaxOvershoot
        ):  # Heat setpoint significantly exceeded so active heat and turn off cooling
            if time.time() - last_heat_time > CONST.HEAT_IDLE_TIME:

                if heat_status == "OFF":
                    last_heat_time = set_device_status("heating", "ON")
                    heat_status = "ON"
                if cool_status == "ON":
                    last_cool_time = set_device_status("cooling", "OFF")
                    cool_status = "OFF"
                    dehumidifier_status = "OFF"
                    state_change = 1

        # #########################
        # HUMIDITY CONTROL LOGIC
        # #########################

        if (
            chamber_humidity >= (CurrentHumiditySetpoint + CurrentHumidityMaxOvershoot)
            and ControlHumidity == "YES"
        ):

            # unlikely as humidifier is now on its own timer
            if humidifier_status == "ON":
                last_humid_time = set_device_status("humidifier", "OFF")
                humidifier_status = "OFF"
                state_change = 1

            # heating and cooling at same time to lower humidity
            if (
                chamber_humidity
                >= CurrentHumiditySetpoint + CurrentHumidityMaxOvershoot
            ):

                if time.time() - last_cool_time > CONST.COMPRESSOR_IDLE_TIME:
                    last_heat_time = set_device_status("heating", "ON")
                    last_cool_time = set_device_status("cooling", "ON")
                    cool_status = "ON"
                    heat_status = "ON"

                dehumidifier_status = "ON"  # only if exceeds DELTA

        if (
            chamber_humidity <= (CurrentHumiditySetpoint - CurrentHumidityMaxOvershoot)
            and ControlHumidity == "YES"
        ):

            if cool_status == "ON":
                last_cool_time = set_device_status("cooling", "OFF")
                cool_status = "OFF"
                dehumidifier_status = "OFF"

                state_change = 1
            else:
                if chamber_humidity <= (
                    CurrentHumiditySetpoint - CurrentHumidityMaxOvershoot
                ):  # Need to humidfy if control delta is crossed
                    if time.time() - last_humid_time >= CONST.HUMIDIFIER_IDLE_TIME:

                        last_humid_time = set_device_status("humidifier", "ON")
                        humidifier_status = "ON"

                        time.sleep(CONST.HUMIDIFIER_DUTY)

                        last_humid_time = set_device_status("humidifier", "OFF")

                        state_change = 1

            # Write status to log
            # Only if something changed

        if (
            state_change == 1
            or chamber_temperature != last_chamber_temperature
            or chamber_humidity != last_chamber_humidity
        ):

            event = "State:"
            if cool_status == "ON":
                event = event + "Cooling, "
            if heat_status == "ON":
                event = event + "Heating, "
            if humidifier_status == "ON":
                event = event + "Humidifying, "
            if dehumidifier_status == "ON":
                event = event + "Dehumidifying, "
            # if air_pump_status == "ON":
            #     event = event + "Flushing "
            event = event + "TempQuorum" + temp_quorum_code + ", "
            event = event + "HumiQuorum" + humidity_quorum_code + ", "
            write_logs(chamber_temperature, chamber_humidity, event)

            if (temp_quorum_code == "No Sensors Agree") or (humidity_quorum_code == "No Sensors Agree"):
                body = "Temp Quorum Code is " + temp_quorum_code + "\nHumidity Quorum Code is " + humidity_quorum_code   
                send_alert("Chamber Environmental Sensors Disagree", body)

            state_change = 0

            # change status after writing to sheet, otherwise won't show up.
            # Not following the logic here for any of the "won't show up" items. Verify.....
            humidifier_status = "OFF"

        last_chamber_temperature = chamber_temperature
        last_chamber_humidity = chamber_humidity

        time.sleep(float(CONST.SLEEP_SECONDS))

    except KeyboardInterrupt:

        print("Quit - Cleaning up devices.")
        # Turn everything OFF
        last_cool_time = set_device_status("cooling", "OFF")
        last_heat_time = set_device_status("heating", "OFF")
        last_humid_time = set_device_status("humidifier", "OFF")
        last_humid_time = set_device_status("dehumidifier", "OFF")
        # last_air_pump_off_time = set_device_status("air", "OFF")

        send_alert(
            "Picuterie Shutdown FROM CONSOLE",
            "Shutdown all controls at " + last_cool_time,
        )

        sys.exit(0)
