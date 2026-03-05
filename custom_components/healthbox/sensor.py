"""Sensor platform for healthbox."""
from __future__ import annotations

from decimal import Decimal
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_MILLION,
    REVOLUTIONS_PER_MINUTE,
    UnitOfPower,
    UnitOfPressure,
    UnitOfVolumeFlowRate,
    UnitOfElectricPotential,
    UnitOfTime
)


from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)


from .const import DOMAIN, MANUFACTURER, HealthboxRoom, LOGGER
from .coordinator import HealthboxDataUpdateCoordinator


@dataclass
class HealthboxGlobalEntityDescriptionMixin:
    """Mixin values for Healthbox Global entities."""

    value_fn: Callable[[], float | int | str | Decimal | None]


@dataclass
class HealthboxGlobalSensorEntityDescription(
    SensorEntityDescription, HealthboxGlobalEntityDescriptionMixin
):
    """Class describing Healthbox Global sensor entities."""


@dataclass
class HealthboxRoomEntityDescriptionMixin:
    """Mixin values for Healthbox Room entities."""

    room: HealthboxRoom
    value_fn: Callable[[], float | int | str | Decimal | None]


@dataclass
class HealthboxRoomSensorEntityDescription(
    SensorEntityDescription, HealthboxRoomEntityDescriptionMixin
):
    """Class describing Healthbox Room sensor entities."""


def _safe_airflow_ventilation_percentage(room: HealthboxRoom) -> float | None:
    """Return airflow ventilation rate in percentage, safely."""
    try:
        value = room.airflow_ventilation_rate
        if value is None:
            return None
        return value * 100
    except Exception as err:
        LOGGER.debug(
            "Unable to read airflow ventilation rate for room '%s' (ID: %s): %s",
            getattr(room, "name", "<unknown>"),
            getattr(room, "room_id", "<unknown>"),
            err,
        )
        return None


def _safe_nested_attr(source: object, *attrs: str) -> float | int | str | Decimal | bool | None:
    """Safely read nested attributes and return None if unavailable."""
    try:
        current = source
        for attr in attrs:
            if current is None:
                return None
            current = getattr(current, attr, None)
        return current
    except Exception as err:
        LOGGER.debug("Unable to read nested attribute '%s': %s", ".".join(attrs), err)
        return None


def _safe_room_boost_level(room: HealthboxRoom) -> float | None:
    """Return room boost level safely."""
    return _safe_nested_attr(room, "boost", "level")


def _safe_room_boost_remaining(room: HealthboxRoom) -> int | None:
    """Return room boost remaining time safely."""
    return _safe_nested_attr(room, "boost", "remaining")


def _safe_room_profile_name(room: HealthboxRoom) -> str | None:
    """Return room profile name safely."""
    return _safe_nested_attr(room, "profile_name")


def generate_room_sensors_for_healthbox(
    coordinator: HealthboxDataUpdateCoordinator,
) -> list[HealthboxRoomSensorEntityDescription]:
    """Generate sensors for each room.

    Previously these sensors were only created when the library reported
    ``advanced_api_enabled`` which required an API key.  That prevented almost
    everything except the boost binary sensor from ever being added if no key
    was used.  The data necessary for temperature/humidity/etc. is actually
    available without "advanced" features, so we remove the gating and instead
    base creation on the presence of real sensor values.

    When the integration is reloaded or updated the sensor list is rebuilt
    every time.  We log what is being generated so that users can check the
    Home Assistant log and verify the code actually attempted to create the
    entities (room list might be empty if data failed to fetch).
    """
    room_sensors: list[HealthboxRoomSensorEntityDescription] = []
    LOGGER.debug("Generating room sensors; coordinator provides %d rooms", len(coordinator.api.rooms))

    # iterate all rooms regardless of advanced_api_enabled; we'll still verify
    # individual sensor data before appending each description
    for room in coordinator.api.rooms:
        LOGGER.debug("Creating sensors for room %s (id=%s)", room.name, room.room_id)
        # Always create temperature sensor regardless of current data state
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_temperature",
                name=f"{room.name} Temperature",
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                icon="mdi:thermometer",
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: x.indoor_temperature,
                suggested_display_precision=2,
            ),
        )
        LOGGER.debug("Added temperature sensor description for room %s", room.name)
        # Always create humidity sensor regardless of current data state
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_humidity",
                name=f"{room.name} Humidity",
                native_unit_of_measurement=PERCENTAGE,
                icon="mdi:water-percent",
                device_class=SensorDeviceClass.HUMIDITY,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: x.indoor_humidity,
                suggested_display_precision=2,
            ),
        )
        # Always create CO2 sensor regardless of current data state
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_co2_concentration",
                name=f"{room.name} CO2 Concentration",
                native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
                icon="mdi:molecule-co2",
                device_class=SensorDeviceClass.CO2,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: x.indoor_co2_concentration,
                suggested_display_precision=2,
            ),
        )
        # Always create AQI sensor regardless of current data state
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_aqi",
                name=f"{room.name} Air Quality Index",
                native_unit_of_measurement=None,
                icon="mdi:leaf",
                device_class=SensorDeviceClass.AQI,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: x.indoor_aqi,
                suggested_display_precision=2,
            ),
        )
        # Always create VOC sensor regardless of current data state
        # (using getattr for safety in case property doesn't exist)
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_voc",
                name=f"{room.name} Volatile Organic Compounds",
                native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
                icon="mdi:leaf",
                device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: getattr(x, 'indoor_voc_ppm', None),
                suggested_display_precision=2,
            ),
        )

    for room in coordinator.api.rooms:
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_boost_level",
                name=f"{room.name} Boost Level",
                native_unit_of_measurement=PERCENTAGE,
                icon="mdi:fan",
                # device_class=SensorDeviceClass.,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_room_boost_level(x),
                suggested_display_precision=2,
            ),
        )
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_boost_remaining",
                name=f"{room.name} Boost Remaining",
                native_unit_of_measurement=UnitOfTime.SECONDS,
                icon="mdi:clock-time-five-outline",
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_room_boost_remaining(x)
            ),
        )
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_airflow_ventilation_rate",
                name=f"{room.name} Airflow Ventilation Rate",
                native_unit_of_measurement=PERCENTAGE,
                icon="mdi:fan",
                # device_class=SensorDeviceClass.,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_airflow_ventilation_percentage(x),
                suggested_display_precision=2,
            ),
        )
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_profile",
                name=f"{room.name} Profile",
                icon="mdi:account-box",
                room=room,
                value_fn=lambda x: _safe_room_profile_name(x),
            ),
        )
        # Flow rate sensors
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_flow_rate",
                name=f"{room.name} Flow Rate",
                native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
                icon="mdi:air-filter",
                device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_nested_attr(x, "flow_rate"),
                suggested_display_precision=2,
            ),
        )
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_nominal_flow_rate",
                name=f"{room.name} Nominal Flow Rate",
                native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
                icon="mdi:air-filter",
                device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_nested_attr(x, "nominal_flow_rate"),
                suggested_display_precision=2,
            ),
        )
        # Power/voltage monitoring
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_measured_power",
                name=f"{room.name} Measured Power",
                native_unit_of_measurement=UnitOfPower.WATT,
                icon="mdi:flash",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_nested_attr(x, "measured_power"),
                suggested_display_precision=1,
            ),
        )
        room_sensors.append(
            HealthboxRoomSensorEntityDescription(
                key=f"healthbox_{room.room_id}_measured_voltage",
                name=f"{room.name} Measured Voltage",
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                icon="mdi:sine-wave",
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                room=room,
                value_fn=lambda x: _safe_nested_attr(x, "measured_voltage"),
                suggested_display_precision=1,
            ),
        )
    return room_sensors


def generate_global_sensors_for_healthbox(
    coordinator: HealthboxDataUpdateCoordinator,
) -> list[HealthboxGlobalSensorEntityDescription]:
    """Generate global sensors."""
    global_sensors: list[HealthboxGlobalSensorEntityDescription] = []
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="global_aqi",
            name="Global Air Quality Index",
            native_unit_of_measurement=None,
            icon="mdi:leaf",
            device_class=SensorDeviceClass.AQI,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: x.global_aqi,
            suggested_display_precision=2,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="error_count",
            name="Error Count",
            native_unit_of_measurement=None,
            icon="mdi:alert-outline",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: x.error_count,
            suggested_display_precision=0,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="wifi_status",
            name="WiFi Status",
            icon="mdi:wifi",
            value_fn=lambda x: _safe_nested_attr(x, "wifi", "status"),
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="wifi_internet_connection",
            name="WiFi Internet Connection",
            native_unit_of_measurement=None,
            icon="mdi:web",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "wifi", "internet_connection"),
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="wifi_ssid",
            name="WiFi SSID",
            icon="mdi:wifi-settings",
            value_fn=lambda x: _safe_nested_attr(x, "wifi", "ssid"),
        )
    )

    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="fan_voltage",
            name="Fan Voltage",
            icon="mdi:sine-wave",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "fan", "voltage"),
            suggested_display_precision=2,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="fan_pressure",
            name="Fan Pressure",
            icon="mdi:arrow-collapse-vertical",
            native_unit_of_measurement=UnitOfPressure.PA,
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "fan", "pressure"),
            suggested_display_precision=2,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="fan_flow",
            name="Fan Flow",
            icon="mdi:wind-power",
            native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
            device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "fan", "flow"),
            suggested_display_precision=2,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="fan_power",
            name="Fan Power",
            icon="mdi:flash",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "fan", "power"),
            suggested_display_precision=2,
        )
    )
    global_sensors.append(
        HealthboxGlobalSensorEntityDescription(
            key="fan_rpm",
            name="Fan RPM",
            icon="mdi:fan",
            native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda x: _safe_nested_attr(x, "fan", "rpm"),
        )
    )

    return global_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: HealthboxDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    global_sensors = generate_global_sensors_for_healthbox(
        coordinator=coordinator)
    room_sensors = generate_room_sensors_for_healthbox(coordinator=coordinator)
    entities = []

    for description in global_sensors:
        entities.append(HealthboxGlobalSensor(coordinator, description))
    for description in room_sensors:
        entities.append(HealthboxRoomSensor(coordinator, description))

    async_add_entities(entities)


class HealthboxGlobalSensor(
    CoordinatorEntity[HealthboxDataUpdateCoordinator], SensorEntity
):
    """Representation of a Healthbox  Room Sensor."""

    entity_description: HealthboxGlobalSensorEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxGlobalSensorEntityDescription,
    ) -> None:
        """Initialize Sensor Domain."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{
            coordinator.config_entry.entry_id}-{description.key}"
        self._attr_name = f"Healthbox {description.name}"
        self._attr_device_info = DeviceInfo(
            name=f"{coordinator.api.serial}",
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=coordinator.api.description,
            hw_version=coordinator.api.warranty_number,
            sw_version=coordinator.api.firmware_version,
        )

    @property
    def native_value(self) -> float | int | str | Decimal:
        """Sensor native value."""
        try:
            return self.entity_description.value_fn(self.coordinator.api)
        except Exception as err:
            LOGGER.debug(
                "Unable to read global sensor value '%s': %s",
                self.entity_description.key,
                err,
            )
            return None


class HealthboxRoomSensor(
    CoordinatorEntity[HealthboxDataUpdateCoordinator], SensorEntity
):
    """Representation of a Healthbox Room Sensor."""

    entity_description: HealthboxRoomSensorEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomSensorEntityDescription,
    ) -> None:
        """Initialize Sensor Domain."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{
            coordinator.config_entry.entry_id}-{description.room.room_id}-{description.key}"
        self._attr_name = f"Healthbox {description.name}"
        self._attr_device_info = DeviceInfo(
            name=self.entity_description.room.name,
            identifiers={
                (
                    DOMAIN,
                    f"{coordinator.config_entry.unique_id}_{
                        self.entity_description.room.room_id}",
                )
            },
            manufacturer="Renson",
            model="Healthbox Room",
        )

    @property
    def native_value(self) -> float | int | str | Decimal:
        """Sensor native value."""
        room_id: int = int(self.entity_description.room.room_id)

        matching_room = [
            room for room in self.coordinator.api.rooms if int(room.room_id) == room_id
        ]

        if len(matching_room) != 1:
            error_msg: str = f"No matching room found for id {room_id}"
            LOGGER.error(error_msg)
        else:
            matching_room = matching_room[0]
            try:
                return self.entity_description.value_fn(matching_room)
            except Exception as err:
                LOGGER.debug(
                    "Unable to read sensor value '%s' for room '%s' (ID: %s): %s",
                    self.entity_description.key,
                    getattr(matching_room, "name", "<unknown>"),
                    room_id,
                    err,
                )
                return None

        return None
