# -*- coding: utf-8 -*-
import asyncio
import logging
import time

import adafruit_scd30
import board
import busio
from cbpi.api import *
from cbpi.api.config import ConfigType
from cbpi.api.dataclasses import NotificationAction, NotificationType

logger = logging.getLogger(__name__)

cache = {}


class SCD30_Config(CBPiExtension):

    def __init__(self, cbpi):
        self.cbpi = cbpi
        self._task = asyncio.create_task(self.init_sensor())

    async def init_sensor(self):
        plugin = await self.cbpi.plugin.load_plugin_list("cbpi4-scd30-CO2-Sensor")
        self.version = plugin[0].get("Version", "0.0.0")
        self.name = plugin[0].get("Name", "cbpi4-scd30-CO2-Sensor")

        self.scd30_update = self.cbpi.config.get(self.name + "_update", None)

        global SCD30_Active
        SCD30_Active = False
        await self.scd30_interval()
        self.Interval = self.cbpi.config.get("scd30_interval", 5)
        i2c = busio.I2C(board.SCL, board.SDA)
        self.scd30 = adafruit_scd30.SCD30(i2c)
        self.scd30.self_calibration_enabled = True
        self.scd30.scd_measurement_interval = self.Interval
        retries = 30
        logging.info("Probing SCD30 sensor...")
        ready = None
        while ready is None and retries:
            try:
                ready = self.scd30.data_available
                SCD30_Active = True
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
            SCD30_Active = True
            try:
                asyncio.create_task(self.ReadSensor())
            except Exception as e:
                logging.error(f"Error while starting sensor readout: {e}")
            except KeyboardInterrupt:
                logging.info("Exiting...")

    async def scd30_interval(self):
        global scd30_interval
        scd30_interval = self.cbpi.config.get("scd30_interval", None)
        if scd30_interval is None:
            logger.info("INIT scd30_intervall")
            try:
                await self.cbpi.config.add(
                    "scd30_interval",
                    5,
                    type=ConfigType.SELECT,
                    description="SCD30 Readout Interval",
                    source=self.name,
                    options=[
                        {"label": "2s", "value": 2},
                        {"label": "5s", "value": 5},
                        {"label": "10s", "value": 10},
                        {"label": "15s", "value": 15},
                        {"label": "30s", "value": 30},
                        {"label": "60s", "value": 60},
                    ],
                )

                scd30_interval = self.cbpi.config.get("scd30_interval", None)
            except:
                logger.warning("Unable to update database")
        else:
            if self.scd30_update == None or self.scd30_update != self.version:
                try:
                    await self.cbpi.config.add(
                        "scd30_interval",
                        scd30_interval,
                        type=ConfigType.SELECT,
                        description="SCD30 Readout Interval",
                        source=self.name,
                        options=[
                            {"label": "2s", "value": 2},
                            {"label": "5s", "value": 5},
                            {"label": "10s", "value": 10},
                            {"label": "15s", "value": 15},
                            {"label": "30s", "value": 30},
                            {"label": "60s", "value": 60},
                        ],
                    )

                except:
                    logger.warning("Unable to update database")

        if self.scd30_update == None or self.scd30_update != self.version:
            try:
                await self.cbpi.config.add(
                    self.name + "_update",
                    self.version,
                    type=ConfigType.STRING,
                    description="SCD30 Version update",
                    source="hidden",
                )
            except Exception as e:
                logger.warning("Unable to update database")
                logger.warning(e)

    async def ReadSensor(self):
        logging.info("Starting scd30 ReadSensor Loop")
        global cache
        while True:
            try:
                if self.scd30.data_available:
                    temp = self.scd30.temperature
                    rh = self.scd30.relative_humidity
                    co2 = self.scd30.CO2
                    timestamp = time.time()
                    cache = {
                        "Time": timestamp,
                        "Temperature": temp,
                        "CO2": co2,
                        "RH": rh,
                    }
                    await asyncio.sleep(self.Interval)
                else:
                    await asyncio.sleep(0.2)
            except Exception as e:
                logging.error("Error while readig SCD30 Sensor: {}".format(e))


@parameters(
    [
        Property.Select(
            "Type",
            options=["CO2", "Temperature", "Relative Humidity"],
            description="Select type of data to register for this sensor.",
        ),
        Property.Number(
            "AlarmLimit",
            description="Limit for an Alarm (e.g. CO2 concentration). Reset is done via Sensor Actions",
        ),
        Property.Select(
            "AlarmType",
            options=["Single", "Continuous"],
            description="Single or Continuous Alarm with every reading.",
        ),
    ]
)
class SCD30Sensor(CBPiSensor):

    def __init__(self, cbpi, id, props):
        super(SCD30Sensor, self).__init__(cbpi, id, props)
        self.value = 0
        self.Type = self.props.get("Type", "CO2")
        self.AlarmType = self.props.get("AlarmType", "Single")
        self.AlarmLimit = float(self.props.get("AlarmLimit", -9999))
        self.time_old = 0
        self.SendAlarm = True if self.AlarmLimit != -9999 else False
        global SCD30_Active
        global cache

    @action(key="Reset Alarm", parameters=[])
    async def Reset(self, **kwargs):
        if self.AlarmType != "Continuous":
            self.reset()
            logging.info("Reset Alarm for SCD30Sensor")
        pass

    def reset(self):
        self.SendAlarm = True

    async def ok(self):
        pass

    async def run(self):
        while self.running is True:
            try:
                if float(cache["Time"]) > float(self.time_old):
                    self.time_old = float(cache["Time"])
                    if self.Type == "CO2":
                        self.value = round(float(cache["CO2"]), 2)
                    elif self.Type == "Temperature":
                        self.value = round(float(cache["Temperature"]), 2)
                    elif self.Type == "Relative Humidity":
                        self.value = round(float(cache["RH"]), 2)
                    self.log_data(self.value)
                    self.push_update(self.value)
                    if self.value > self.AlarmLimit and self.AlarmLimit != -9999:
                        if self.SendAlarm:
                            if self.AlarmType != "Continuous":
                                self.cbpi.notify(
                                    "SCD30 Sensor Alarm",
                                    "{}  (Value: {}) is above limit of {}".format(
                                        self.Type, self.value, self.AlarmLimit
                                    ),
                                    NotificationType.WARNING,
                                    action=[NotificationAction("OK", self.ok)],
                                )
                                self.SendAlarm = False
                            else:
                                self.cbpi.notify(
                                    "SCD30 Sensor Alarm",
                                    "{}  (Value: {}) is above limit of {}".format(
                                        self.Type, self.value, self.AlarmLimit
                                    ),
                                    NotificationType.WARNING,
                                )
                    if self.value < self.AlarmLimit and self.SendAlarm == False:
                        self.SendAlarm = True

                self.push_update(self.value, False)
                # self.cbpi.ws.send(dict(topic="sensorstate", id=self.id, value=self.value))
            except Exception as e:
                pass
            await asyncio.sleep(1)

    def get_state(self):
        return dict(value=self.value)


def setup(cbpi):
    cbpi.plugin.register("SCD30 Sensor", SCD30Sensor)
    cbpi.plugin.register("SDC30 Config", SCD30_Config)
    pass
