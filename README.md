# CraftBeerPi4 SCD30 based CO2 Sensor Plugin

### Sensors	

Plugin will add system a sensor to monitor for instance CO2 monitoring in your fermentation room

![Sensor Config](https://github.com/avollkopf/cbpi4-scd30-co2-sensor/blob/main/cbpi4-scd30-settings.png?raw=true)
	
- CO2: 					CO2 value in ppm
- Relative Humidity:	Relative humidity in %
- Temperatur:			Temperature

Each parameter has to be added as individual sensor.
	
![Multiple Sensors](https://github.com/avollkopf/cbpi4-scd30-co2-sensor/blob/main/cbpi4-multiple-scd30.png?raw=true)

### Installation: 
- sudo pip3 install cbpi4-scd30_CO2_Sensor
- or install from repo: sudo pip3 install https://github.com/avollkopf/cbpi4-scd30-co2-sensor/archive/main.zip
- cbpi add cbpi4-scd30_CO2_Sensor
	
### Usage:

- Configure the update interval of the sensor data in the cbpi global settings. Although shorter cycles ar possible, 30 or 60 seconds should be more than sufficient.

![Global Sensor Interval Settings](https://github.com/avollkopf/cbpi4-scd30-co2-sensor/blob/main/cbpi4-scd30-settings-interval.png?raw=true)

- Add Hardware under Sensor and choose SCD30 Sensor as Type and select the parameter you want to monitor.

### Hardware requirements:

A datasheet of the sensor can be found here: https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_CO2_Sensors_SCD30_Datasheet.pdf

Information on how read from then sensor is documented here: https://cdn.sparkfun.com/assets/d/c/0/7/2/SCD30_Interface_Description.pdf

The sensor is connected via I2C and has the address 0x61. The user just needs to activate I2C in the raspi config and connect the sensor to the I2C bus. The supply voltage (VDD) can be 5V, but the I2C bus has to be at 3.3V

### Changelog:

- 16.01.22: (0.0.3) adaption for cbpi 4.0.1.2
- 12.01.22: (0.0.2) Reduction of mqtt traffic
- 23.07.21: (0.0.1) Initial commit
