
# -*- coding: utf-8 -*-
import os, threading
from aiohttp import web
import logging
from unittest.mock import MagicMock, patch
import asyncio
import random
from cbpi.api import *
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
from scd30_i2c import SCD30
import time

logger = logging.getLogger(__name__)

cache = {}

class SCD30_Config(CBPiExtension):

    def __init__(self,cbpi):
        self.cbpi = cbpi
        self._task = asyncio.create_task(self.init_sensor())

    async def init_sensor(self):
        global SCD30_Active
        SCD30_Active=False
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
            loop = asyncio.get_event_loop()
            try:
                asyncio.ensure_future(self.ReadSensor())
                loop.run_forever()
            finally:
                loop.close()



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
                                                                                                            {"label": "30s", "value": 30},
                                                                                                            {"label": "60s", "value": 60}])
                scd30_interval = self.cbpi.config.get("scd30_interval", None)
            except:
                logger.warning('Unable to update database')


    async def ReadSensor(self):
        logging.info("Starting scd30 ReadSensor Loop")
        global cache
        while True:
            if self.scd30.get_data_ready():
                measurement = self.scd30.read_measurement()
                if measurement is not None:
                    co2, temp, rh = measurement
                    timestamp = time.time()
                    cache = {'Time': timestamp,'Temperature': temp, 'CO2': co2, 'RH': rh}
                await asyncio.sleep(self.Interval)
            else:
                await asyncio.sleep(0.2)


@parameters([Property.Select("Type", options=["CO2", "Temperature", "Relative Humidity"], description="Select type of data to register for this sensor.")])
class SCD30Sensor(CBPiSensor):
    
    def __init__(self, cbpi, id, props):
        super(SCD30Sensor, self).__init__(cbpi, id, props)
        self.value = 0
        self.Type = self.props.get("Type","CO2")
        self.time_old = 0
        global SCD30_Active
        global cache

    async def run(self):
        while self.running is True:
            try:
                if (float(cache['Time']) > float(self.time_old)):
                    self.time_old = float(cache['Time'])
                    if self.Type == "CO2":
                        self.value = round(float(cache['CO2']),2)
                    elif self.Type == "Temperature":
                        self.value = round(float(cache['Temperature']),2)
                    elif self.Type == "Relative Humidity":
                        self.value = round(float(cache['RH']),2)
                    self.log_data(self.value)
                self.push_update(self.value)

            except Exception as e:
                pass
            await asyncio.sleep(1)

   
    def get_state(self):
        return dict(value=self.value)

def setup(cbpi):
    cbpi.plugin.register("SCD30 Sensor", SCD30Sensor)
    cbpi.plugin.register("SDC30 Config", SCD30_Config)
    pass
