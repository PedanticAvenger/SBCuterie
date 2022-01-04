# SBCuterie
Raspberry Pi control for meat curing chamber
This started as a straight fork of https://github.com/hjbct44/PorkPi where I wanted to change out the DHT22 sensors for SEEED Grove I2C based AHT20 sensors (3 of them with quorum sensing for detecting sensor failure) and I2C controlled relays to achieve the cabling flexibility I'm looking for and all controlled with SMBus.  With some consideration I decided to remove the google sheet integration (at least initially) to have a system that did not depend on Internet access to be able to function.  This prompted a move to SQLite on-board to hold settings and logs and a simple on-board web interface to control.  For initial release these functions are basic and are a good area for future expansion.

For context, I am building this for a True  commercial refrigerator that I would like to physically modify as little as possible.  I plan to disconnect the current thermostat wires and replace it with one of the relays for cooling control, the only other physical mod is one hole large enough for the mains electrical feed to come in at the bottom of the fridge (plugless, wired into relay board) and the air pump power cable (small plug) and air hose.

Removed load sensors from PorkPi but if I can setup reliable load cell options they may come back (i.e. If I can deal with the drift involved with most resistive load cells, a problem over the longer term operation required for a long dry cure, weight loss will be typically under-reported in this application.).  But to be honest I will probably leave a scale by the fridge and start checking regularly around the expected readiness date for the items.

Also the project will eventually include some 3d printing models for enclosures to hold the sensors I'm using, I2C multiplexer, Grove to RJ45 adapters, etc.  Pi can live outside the fridge and one cat5/6 cable can run into the fridge to connect to sensors, run relays, etc.

I am still rather new to python and will certainly consider PRs that expand the functionality.  Preference given to PRs that don't change defaults but expand capabilities so things aren't broken for any other potential users.

Further down the road (mostly cause I can't make it stable yet due to my lack of understanding on the details of this so far) migrating the simple on/off rules to a fuzzy logic PID-type control for more environmental stability.  

Highlights:
The system will have control for the following inputs.
          Cooling on/off
          Heating on/off
          Humidifier on/off
          De-humidifier on/off
          Air pump on/off (for air exchange automatically if I can't be there regularly to open door, not implemented in first releases as the 4 relays on my module already used up and I need to determine how I want to handle that.) 

Environmental control settings and logging is stored in a SQLite database, plan to add supplementary logging options to things like syslog, splunk/ELK, etc.

Restarts/crashes are reported via email. 

Software watchdog from PorkPi kept.

Using python http.server library to build on-board control interface which will be integrated into the monitoring scripts, etc. 

Files:
 
  rc.local
  1. Starts the system on reboot, put in the /etc directory
  2. Waits for LAN to come up.
  3. Runs RebootMailer
  4. Starts StartPicuterie.sh shell script using screen (https://www.gnu.org/software/screen/manual/screen.html#Overview) to allow remote login to headless application

 ./RebootMailer
  1. send email saying system rebooted
   
 ./WaitForLan.sh
  1. loop until get successful ping from LAN

 ./StartPicuterie.sh
  1. start hardware watchdog (/etc/init.d/watchdog)
  2. start software watchdog (PicuterieWatchDog.sh)
  3. send email saying Picuterie started
  4. execute python code Picuterie.py
  5. if Picuterie.py crashes, send email saying crashed, attach error log and restart Picuterie.py

./PicuterieWatchDog.sh
  1. touch file
  2. check file has been touched by Picuterie.py recently
  3. if file has not been touched recently, reboot
  4. execute PicuterieCheckEmail.py to check to see if received email for reboot or restart   

 ./Picuterie.py
  Main python code for Picuterie

./includes/AHT20.py
  hardware python library for AHT20 temperature/humidity Sensors
  
./includes/grove_i2c_relay_regular.py
  hardware python library for Grove 4/8 port I2C controlled relay board.
  
./includes/TCA9548A.py
  hardware python library for I2C MUX
  
./includes/const.py
  Holds all the tuneable constants used in SBCuterie to allow modification without diving into the main code
  
./includes/inidializedb.py
  Python script to setup/reset the SQLite DB for the system

  
