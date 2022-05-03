#!/usr/bin/python

"""
This script should only be run on the initialization of your Picuterie
system.  It will create the SQLite database and initialize the required
tables with some basic data.

If the filename exists it will be overwritten.

Variables are stored in the DB in metric with conversion to imperial if 
required.  The default is considered to be metric across the system.
"""

from pathlib import Path
import sqlite3

myfile = Path("PiCuterieDB.db")
f = open(myfile, "w+")


conn = sqlite3.connect("PiCuterieDB.db")
print("Opened database successfully")


conn.execute(
    """CREATE TABLE CTRLSETTING 
    (ID INT PRIMARY KEY NOT NULL, 
    ProfileLabel TEXT NOT NULL, 
    AirPumpDuty INT NOT NULL,
    AirPumpIdleTime INT NOT NULL, 
    LogServerStatus INT NOT NULL, 
    CommandEmailStatus TEXT NOT NULL,
    CommandEmailAddress TEXT NOT NULL, 
    NotificationEmailAddress TEXT NOT NULL, 
    ReportingConfig INT NOT NULL, 
    GoogleSheetID  TEXT NOT NULL, 
    ScheduleStatus INT NOT NULL,
    ScheduleID INT NOT NULL);"""
)

print("Control Settings Table created")

conn.execute(
    "INSERT INTO CTRLSETTING (ID,ProfileLabel,AirPumpDuty,AirPumpIdleTime,LogServerStatus,CommandEmailStatus,CommandEmailAddress,NotificationEmail,ReportingConfig,GoogleSheetID,ScheduleStatus,ScheduleID) \
      VALUES (1, 'Default', 120, 2600 0, NO, 'yourcmd@email.com', 'Your@email.com', 0, 'Unset', '0', '0');"
)

print("Control Settings Table populated with default data")

conn.execute(
    """CREATE TABLE ENVSETTING
    (ID INT PRIMARY KEY NOT NULL, 
    ProfileLabel TEXT NOT NULL, 
    CurrentTempSetPoint REAL NOT NULL,
    CurrentTempMaxOvershoot REAL NOT NULL,
    CurrentHumiditySetpoint REAL NOT NULL,
    CurrentHumidityMaxOvershoot REAL NOT NULL,
    ControlHumidity TEXT NOT NULL,
);"""
)

print("Environment Settings Table created successfully")

conn.execute(
    "INSERT INTO ENVSETTING (ID,ProfileLabel,CurrentTempSetPoint,CurrentTempMaxOvershoot,ControlTemperature,CurrentHumiditySetpoint,CurrentHumidityMaxOvershoot,ControlHumidity) \
      VALUES (1, 'Default', 13, 2, 85, 3, YES);"
)

print("Environment Settings Table populated with default data")

conn.execute(
    """CREATE TABLE SCHEDULE 
    (SchedID INT NOT NULL,
    StartTime TEXT NOT NULL,
    TempSetPoint REAL NOT NULL,
    HumiditySetPoint REAL NOT NULL);"""
)

conn.execute(
    "INSERT INTO SCHEDULE (SchedID,StartTime,TempSetPoint,HumiditySetPoint) \
      VALUES (0,datetime('now', 'localtime'), 13, 85);"
)

conn.execute(
    """CREATE TABLE ENVIROLOG
    (Time INT NOT NULL,
    Temperature REAL NOT NULL,
    Humidity REAL NOT NULL);"""
)

conn.execute(
    """CREATE TABLE EVENTLOG
    (Time INT NOT NULL,
    Event TEXT);"""
)

conn.commit()
print("Settings records created successfully")

conn.close()
