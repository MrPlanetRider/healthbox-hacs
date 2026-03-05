"""Constants for the Renson Healthbox integration."""
import voluptuous as vol

from logging import Logger, getLogger
from datetime import timedelta
from decimal import Decimal

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

LOGGER: Logger = getLogger(__package__)

NAME = "Healthbox "
DOMAIN = "healthbox"
VERSION = "1.1.2"
MANUFACTURER = "Renson"
ATTRIBUTION = ""
SCAN_INTERVAL = timedelta(seconds=5)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

SERVICE_CHANGE_ROOM_PROFILE = "change_room_profile"
SERVICE_CHANGE_ROOM_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("profile_name"): cv.string
    }
)

SERVICE_START_ROOM_BOOST = "start_room_boost"
SERVICE_START_ROOM_BOOST_SCHEMA = vol.Schema(
    {
        vol.Required(cv.CONF_DEVICE_ID): cv.string,
        vol.Required("boost_level"): vol.All(int, vol.Range(min=10, max=200)),
        vol.Required("boost_timeout"): vol.All(int, vol.Range(min=5, max=720)),
    }
)

SERVICE_STOP_ROOM_BOOST = "stop_room_boost"
SERVICE_STOP_ROOM_BOOST_SCHEMA = vol.Schema(
    {vol.Required("device_id"): cv.string},
)

ALL_SERVICES = [
    SERVICE_START_ROOM_BOOST,
    SERVICE_STOP_ROOM_BOOST,
    SERVICE_CHANGE_ROOM_PROFILE
]


class HealthboxRoomBoost:
    """Healthbox  Room Boost object."""

    level: float
    enabled: bool
    remaining: int

    def __init__(
        self, level: float = 100, enabled: bool = False, remaining: int = 900
    ) -> None:
        """Initialize the HB Room Boost."""
        self.level = level
        self.enabled = enabled
        self.remaining = remaining


class HealthboxRoom:
    """Healthbox  Room object."""

    boost: HealthboxRoomBoost = None

    def __init__(self, room_id: int, room_data: object) -> None:
        """Initialize the HB Room."""
        self.room_id: int = room_id
        self.name: str = room_data["name"]
        self.type: str = room_data["type"]
        self.sensors_data: list = room_data.get("sensor", [])
        self.room_type: str = room_data["type"]
        self.parameters: dict = room_data.get("parameter", {})
        self.actuators: list = room_data.get("actuator", [])

    @property
    def indoor_temperature(self) -> Decimal:
        """HB Indoor Temperature."""
        try:
            for sensor in self.sensors_data:
                param = sensor.get("parameter")
                if isinstance(param, dict) and "temperature" in param:
                    temp = param.get("temperature")
                    if isinstance(temp, dict) and "value" in temp:
                        return temp["value"]
            # If we get here, no temperature sensor with data found
            if self.sensors_data:
                LOGGER.debug(
                    "No valid temperature data for room '%s' (ID: %s). "
                    "Check if sensor is connected to the device.",
                    self.name, self.room_id
                )
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning(
                "Error reading temperature for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def indoor_humidity(self) -> Decimal:
        """HB Indoor Humidity."""
        try:
            for sensor in self.sensors_data:
                param = sensor.get("parameter")
                if isinstance(param, dict) and "humidity" in param:
                    hum = param.get("humidity")
                    if isinstance(hum, dict) and "value" in hum:
                        return hum["value"]
            # If we get here, no humidity sensor with data found
            if self.sensors_data:
                LOGGER.debug(
                    "No valid humidity data for room '%s' (ID: %s). "
                    "Check if sensor is connected to the device.",
                    self.name, self.room_id
                )
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning(
                "Error reading humidity for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def indoor_co2_concentration(self) -> Decimal | None:
        """HB Indoor CO2 Concentration."""
        try:
            # First, try to find room-specific "indoor CO2" sensor
            for sensor in self.sensors_data:
                sensor_type = sensor.get("type", "")
                if sensor_type == "indoor CO2":
                    param = sensor.get("parameter")
                    if isinstance(param, dict) and "concentration" in param:
                        conc = param.get("concentration")
                        if isinstance(conc, dict) and "value" in conc:
                            LOGGER.debug(
                                "Found specific CO2 sensor for room '%s' (ID: %s): %.1f ppm",
                                self.name, self.room_id, conc["value"]
                            )
                            return conc["value"]
            
            # Fall back to "indoor mixed CO2" (shared sensor)
            for sensor in self.sensors_data:
                sensor_type = sensor.get("type", "")
                if sensor_type == "indoor mixed CO2":
                    param = sensor.get("parameter")
                    if isinstance(param, dict) and "concentration" in param:
                        conc = param.get("concentration")
                        if isinstance(conc, dict) and "value" in conc:
                            LOGGER.debug(
                                "Found mixed CO2 sensor for room '%s' (ID: %s): %.1f ppm",
                                self.name, self.room_id, conc["value"]
                            )
                            return conc["value"]
            
            # If we get here, no CO2 sensor with data found
            if self.sensors_data:
                LOGGER.debug(
                    "No valid CO2 data for room '%s' (ID: %s). "
                    "Check if sensor is connected to the device.",
                    self.name, self.room_id
                )
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning(
                "Error reading CO2 for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def indoor_aqi(self) -> Decimal | None:
        """HB Indoor Air Quality Index."""
        try:
            for sensor in self.sensors_data:
                sensor_type = sensor.get("type", "")
                if sensor_type == "indoor air quality index":
                    param = sensor.get("parameter")
                    if isinstance(param, dict) and "index" in param:
                        idx = param.get("index")
                        if isinstance(idx, dict) and "value" in idx:
                            return idx["value"]
            # If we get here, no AQI sensor with data found
            if self.sensors_data:
                LOGGER.debug(
                    "No valid AQI data for room '%s' (ID: %s). "
                    "Check if sensor is connected to the device.",
                    self.name, self.room_id
                )
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning(
                "Error reading AQI for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def indoor_voc_ppm(self) -> Decimal | None:
        """HB Indoor Volatile Organic Compounds in PPM."""
        try:
            for sensor in self.sensors_data:
                sensor_type = sensor.get("type", "")
                if sensor_type == "indoor volatile organic compounds":
                    param = sensor.get("parameter")
                    if isinstance(param, dict) and "concentration" in param:
                        conc = param.get("concentration")
                        if isinstance(conc, dict) and "value" in conc:
                            return conc["value"]
            # If we get here, no VOC sensor with data found
            if self.sensors_data:
                LOGGER.debug(
                    "No valid VOC data for room '%s' (ID: %s). "
                    "Check if sensor is connected to the device.",
                    self.name, self.room_id
                )
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning(
                "Error reading VOC for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def flow_rate(self) -> Decimal | None:
        """Current airflow rate from actuator (m³/h)."""
        try:
            for actuator in self.actuators:
                if actuator.get("type") == "air valve":
                    param = actuator.get("parameter")
                    if isinstance(param, dict) and "flow_rate" in param:
                        flow = param.get("flow_rate")
                        if isinstance(flow, dict) and "value" in flow:
                            return flow["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading flow_rate for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def nominal_flow_rate(self) -> Decimal | None:
        """Nominal/design airflow rate (m³/h)."""
        try:
            if "nominal" in self.parameters:
                nominal = self.parameters.get("nominal")
                if isinstance(nominal, dict) and "value" in nominal:
                    return nominal["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading nominal flow rate for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def doors_open(self) -> bool | None:
        """Door open/closed state."""
        try:
            if "doors_open" in self.parameters:
                doors = self.parameters.get("doors_open")
                if isinstance(doors, dict) and "value" in doors:
                    return doors["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading doors_open for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def doors_present(self) -> bool | None:
        """Whether room has door sensors."""
        try:
            if "doors_present" in self.parameters:
                doors = self.parameters.get("doors_present")
                if isinstance(doors, dict) and "value" in doors:
                    return doors["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading doors_present for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def measured_power(self) -> Decimal | None:
        """Measured power consumption (W)."""
        try:
            if "measured_power" in self.parameters:
                power = self.parameters.get("measured_power")
                if isinstance(power, dict) and "value" in power:
                    return power["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading measured_power for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None

    @property
    def measured_voltage(self) -> Decimal | None:
        """Measured voltage (V)."""
        try:
            if "measured_voltage" in self.parameters:
                voltage = self.parameters.get("measured_voltage")
                if isinstance(voltage, dict) and "value" in voltage:
                    return voltage["value"]
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.debug(
                "Error reading measured_voltage for room '%s' (ID: %s): %s",
                self.name, self.room_id, e
            )
        return None


class HealthboxDataObject:
    """Healthbox Data Object."""

    serial: str
    description: str
    warranty_number: str

    global_aqi: float = None

    rooms: list[HealthboxRoom]

    def __init__(self, data: any) -> None:
        """Initialize."""
        self.serial = data["serial"]
        self.description = data["description"]
        self.warranty_number = data["warranty_number"]

        self.global_aqi = self._get_global_aqi_from_data(data)

        hb_rooms: list[HealthboxRoom] = []
        for room in data["room"]:
            hb_room = HealthboxRoom(room, data["room"][room])
            hb_rooms.append(hb_room)

        self.rooms = hb_rooms

    def _get_global_aqi_from_data(self, data: any) -> float | None:
        """Set Global AQI from Data Object."""
        try:
            sensors = data.get("sensor") or []
            for sensor in sensors:
                if sensor.get("type") == "global air quality index":
                    param = sensor.get("parameter")
                    if isinstance(param, dict) and "index" in param:
                        idx = param.get("index")
                        if isinstance(idx, dict) and "value" in idx:
                            return idx["value"]
            # Log if global AQI sensor exists but has no data
            for sensor in sensors:
                if sensor.get("type") == "global air quality index":
                    LOGGER.debug(
                        "Global AQI sensor found but has no valid index data. "
                        "Check device configuration."
                    )
                    break
        except (TypeError, KeyError, AttributeError) as e:
            LOGGER.warning("Error reading global AQI: %s", e)
        return None
