
# -*- coding: utf-8 -*-
import os
from aiohttp import web
import logging
from unittest.mock import MagicMock, patch
import asyncio
import random
from cbpi.api import *
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
from scd30_i2c import SCD30

logger = logging.getLogger(__name__)



class SCD30_Config(CBPiExtension):

    def __init__(self,cbpi):
        self.cbpi = cbpi
        self._task = asyncio.create_task(self.init_sensor())


    async def init_sensor(self):
        global SCD30_Active
        await self.scd30_interval()
        self.scd30 = SCD30()
        self.Interval = self.cbpi.config.get("scd30_interval", 5)
        retries = 30
        logging.info("Probing SCD30 sensor...")
        ready = None
        while ready is None and retries:
            try:
                ready = self.scd30.get_data_ready()
                SCD30_Active=True
            except OSError:
                # The sensor may need a couple of seconds to boot up after power-on
                # and may not be ready to respond, raising I2C errors during this time.
                pass
            await asyncio.sleep(1)
            retries -= 1
        if not retries:
            logging.error("Timed out waiting for SCD30.")
            pass 
        if ready is not None:    
            logging.info("Link to sensor established.")
            logging.info("Getting firmware version...")
            logging.info(f"Sensor firmware version: {self.scd30.get_firmware_version()}")
            self.scd30.set_measurement_interval(self.Interval)
            logging.info("Enabling automatic self-calibration...")
            self.scd30.set_auto_self_calibration(active=True)
            logging.info("Starting periodic measurement...")
            self.scd30.start_periodic_measurement()
            await asyncio.sleep(self.Interval)
            SCD30_Active=True
            logging.info(f"ASC status: {self.scd30.get_auto_self_calibration_active()}")
            logging.info(f"Measurement interval: {self.scd30.get_measurement_interval()}s")
            logging.info(f"Temperature offset: {self.scd30.get_temperature_offset()}'C")
            pass

    async def scd30_interval(self):
        global scd30_interval
        scd30_interval = self.cbpi.config.get("scd30_interval", None)
        if scd30_interval is None:
            logger.info("INIT scd30_intervall")
            try:
                await self.cbpi.config.add("scd30_interval", 5, ConfigType.SELECT, "SCD30 Readout Interval", [{"label": "2s","value": 2},
                                                                                                            {"label": "5s", "value": 5},
                                                                                                            {"label": "10s", "value": 10},
                                                                                                            {"label": "15s", "value": 15},
                                                                                                            {"label": "60s", "value": 60}])
                scd30_interval = self.cbpi.config.get("scd30_interval", None)
            except:
                logger.warning('Unable to update database')

@parameters([Property.Select("Type", options=["CO2", "Temperature", "Relative Humidity"], description="Select type of data to register for this sensor.")])
class SCD30Sensor(CBPiSensor):
    
    def __init__(self, cbpi, id, props):
        super(SCD30Sensor, self).__init__(cbpi, id, props)
        self.value = 0
        self.SCD30_Active=False
        self.Interval = self.cbpi.config.get("scd30_interval", 5)
        self.scd30 = SCD30()
        self.Type = self.props.get("Type","CO2")
        global SCD30_Active

    async def run(self):
        while self.running is True:
            if SCD30_Active == True:
                if self.scd30.get_data_ready():
                    measurement = self.scd30.read_measurement()
                    if measurement is not None:
                        co2, temp, rh = measurement
#                        print(f"CO2: {co2:.2f}ppm, temp: {temp:.2f}'C, rh: {rh:.2f}%")
                        if self.Type == "CO2":
                            self.value = round(float(co2),2)
                        elif self.Type == "Temperature":
                            self.value = round(float(temp),2)
                        elif self.Type == "Relative Humidity":
                            self.value = round(float(rh),2)
                    await asyncio.sleep(self.Interval)
                else:
                    await asyncio.sleep(0.2)

                self.log_data(self.value)
                self.push_update(self.value)
#                await asyncio.sleep(1)
   
    def get_state(self):
        return dict(value=self.value)

def setup(cbpi):
    cbpi.plugin.register("SCD30 Sensor", SCD30Sensor)
    cbpi.plugin.register("SDC30 Config", SCD30_Config)
    pass
