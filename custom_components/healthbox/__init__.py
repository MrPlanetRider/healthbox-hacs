"""The Renson Healthbox integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .lib.pyhealthbox3.healthbox3 import Healthbox3

from .const import LOGGER

# Monkey-patch pyhealthbox3 to avoid crashes when actuator/sensor parameters are None.
# The library's Room._get_airflow_ventilation_rate accesses nested keys without
# checking for None, leading to 'NoneType' errors if an actuator has null
# parameter. We patch the method to return None instead of raising.

try:
    from .lib.pyhealthbox3.models import Room

    _orig_get_airflow = Room._get_airflow_ventilation_rate

    def _safe_get_airflow(self):
        try:
            return _orig_get_airflow(self)
        except Exception as err:  # catch TypeError, KeyError, etc.
            LOGGER.warning(
                "Patched airflow ventilation rate calculation failed for room %s: %s",
                getattr(self, 'name', '<unknown>'),
                err,
            )
            return None

    Room._get_airflow_ventilation_rate = _safe_get_airflow

    # also patch property to guard further
    if hasattr(Room, 'airflow_ventilation_rate'):
        orig_prop = Room.airflow_ventilation_rate.fget

        def _safe_airflow_prop(self):
            try:
                return orig_prop(self)
            except Exception as err:
                LOGGER.warning(
                    "Patched airflow ventilation_rate property raised %s for room %s",
                    err, getattr(self, 'name', '<unknown>')
                )
                return None

        Room.airflow_ventilation_rate = property(_safe_airflow_prop)
except ImportError:
    # library not available in test environment
    pass


from .const import (
    ALL_SERVICES,
    DOMAIN,
    SERVICE_CHANGE_ROOM_PROFILE,
    SERVICE_CHANGE_ROOM_PROFILE_SCHEMA,
    SERVICE_START_ROOM_BOOST,
    SERVICE_START_ROOM_BOOST_SCHEMA,
    SERVICE_STOP_ROOM_BOOST,
    SERVICE_STOP_ROOM_BOOST_SCHEMA,
    PLATFORMS,
)

from .coordinator import HealthboxDataUpdateCoordinator


def _resolve_device_and_coordinator(
    hass: HomeAssistant, device_id: str
) -> tuple[dr.DeviceEntry, HealthboxDataUpdateCoordinator]:
    """Resolve device and coordinator for a service call device_id."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device not found for device_id '{device_id}'")

    coordinators = hass.data.get(DOMAIN, {})
    for config_entry_id in device.config_entries:
        coordinator = coordinators.get(config_entry_id)
        if coordinator is not None:
            return device, coordinator

    raise ServiceValidationError(
        f"No active Healthbox config entry found for device_id '{device_id}'"
    )


def _extract_room_id(device: dr.DeviceEntry) -> int:
    """Extract the room id from Healthbox device identifiers."""
    for identifier_domain, identifier in device.identifiers:
        if identifier_domain != DOMAIN:
            continue
        try:
            return int(identifier.split("_")[-1])
        except (TypeError, ValueError):
            continue

    raise ServiceValidationError(
        "Unable to determine room id from Healthbox device identifiers"
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services once per domain."""

    async def change_room_profile(call: ServiceCall) -> None:
        """Service to change the HB3 Room Profile."""
        device_id = call.data["device_id"]
        device, coordinator = _resolve_device_and_coordinator(hass, device_id)
        room_id = _extract_room_id(device)
        LOGGER.debug(
            "Service call: %s.%s device_id=%s room_id=%s profile_name=%s",
            DOMAIN,
            SERVICE_CHANGE_ROOM_PROFILE,
            device_id,
            room_id,
            call.data["profile_name"],
        )
        await coordinator.change_room_profile(
            room_id=room_id,
            profile_name=call.data["profile_name"],
        )

    async def start_room_boost(call: ServiceCall) -> None:
        """Service call to start boosting fans in a room."""
        device_id = call.data["device_id"]
        device, coordinator = _resolve_device_and_coordinator(hass, device_id)
        room_id = _extract_room_id(device)
        LOGGER.debug(
            "Service call: %s.%s device_id=%s room_id=%s boost_level=%s boost_timeout_min=%s",
            DOMAIN,
            SERVICE_START_ROOM_BOOST,
            device_id,
            room_id,
            call.data["boost_level"],
            call.data["boost_timeout"],
        )
        await coordinator.start_room_boost(
            room_id=room_id,
            boost_level=call.data["boost_level"],
            boost_timeout=call.data["boost_timeout"] * 60,
        )

    async def stop_room_boost(call: ServiceCall) -> None:
        """Service call to stop boosting fans in a room."""
        device_id = call.data["device_id"]
        device, coordinator = _resolve_device_and_coordinator(hass, device_id)
        room_id = _extract_room_id(device)
        LOGGER.debug(
            "Service call: %s.%s device_id=%s room_id=%s",
            DOMAIN,
            SERVICE_STOP_ROOM_BOOST,
            device_id,
            room_id,
        )
        await coordinator.stop_room_boost(room_id=room_id)

    if not hass.services.has_service(DOMAIN, SERVICE_START_ROOM_BOOST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START_ROOM_BOOST,
            start_room_boost,
            SERVICE_START_ROOM_BOOST_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_ROOM_BOOST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_ROOM_BOOST,
            stop_room_boost,
            SERVICE_STOP_ROOM_BOOST_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CHANGE_ROOM_PROFILE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CHANGE_ROOM_PROFILE,
            change_room_profile,
            SERVICE_CHANGE_ROOM_PROFILE_SCHEMA,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renson Healthbox from a config entry."""
    api_key = None

    if CONF_API_KEY in entry.data:
        api_key = entry.data[CONF_API_KEY]

    # if CONF_API_KEY in entry.options:
    #     api_key = entry.options[CONF_API_KEY]

    api: Healthbox3 = Healthbox3(
        host=entry.data[CONF_HOST],
        api_key=api_key,
        session=async_get_clientsession(hass),
    )
    if api_key:
        LOGGER.debug("API key provided, enabling advanced features")
        await api.async_enable_advanced_api_features()
        LOGGER.debug("Advanced API features enabled: %s", api.advanced_api_enabled)
    else:
        LOGGER.debug("No API key provided, sensor data will be limited")

    coordinator = HealthboxDataUpdateCoordinator(
        hass=hass, entry=entry, api=api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]

        for service in ALL_SERVICES:
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Reload entry if options change."""
    await hass.config_entries.async_reload(entry.entry_id)
