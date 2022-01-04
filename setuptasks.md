Creating a new SBCuterie system from scratch.
Minimum viable items for this codebase and it's assumptions
1) Raspberry Pi or similar dev board (Developed on a model 2B w/ Raspberry Pi OS Lite so not a lot of resources needed, but production on a Rock Pi 4B+ running armbian.  GUI desktop not needed or likely valuable and a future display probably going to be 4x20 LCD.)
2) Qty 1 of Grove 8 channel I2C MUX (https://www.seeedstudio.com/Grove-8-Channel-I2C-Hub-TCA9548A-p-4398.html)
3) Qty 3 of Grove AHT20 Temp/Humidity Sensors (https://wiki.seeedstudio.com/Grove-AHT20-I2C-Industrial-Grade-Temperature%26Humidity-Sensor/)
4) Qty 1 of Grove - 4-Channel SPDT Relay (https://wiki.seeedstudio.com/Grove-4-Channel_SPDT_Relay/)

Not required in addition to above but used in system build during development (no active components but useful adapters, etc.)
1) Qty 4 of Grove - RJ45 Adapter (https://wiki.seeedstudio.com/Grove-RJ45_Adapter/).  These are also a personal preference.  Easy to run a high quality RJ45 cable into the fridge and have one block with MUC and sensors, then a second block w/ relays.  All daisy chained with nice single cable.
2) 3d printed enclosure for Pi w/ shield and a rj45 adapter, 3d printed enclosure to hold 3 aht20 sensors, mux, 2 rj45 adapters (add link or folder in project with files)

Software added to base OS image
Recent python (3.9 or newer, docs and initial code releases developed using 3.10) Install as altinstall and this will run inside a virtual environment.

Screen (https://www.gnu.org/software/screen/manual/screen.html#Overview) used at launch to allow re-connection to the code once running.  Many OS include this already.

Build your virtual environment and for the python modules/libraries, remember to setup inside the virtual environment.
    make sure you have SMBus lib installed as well as your system setup and understood (i.e. where is your I2C bus pins, what the I2C Bus Number is, etc.)
    everything else should be "default" python libs (but this will be updated once a clean install test is done if not....)
    If you are not going to run this as a root user on your SBC then remember to add your user to an i2c group to allow access to the i2c bus
