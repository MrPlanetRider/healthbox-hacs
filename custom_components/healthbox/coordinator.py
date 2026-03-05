"""DataUpdateCoordinator for healthbox."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.exceptions import ConfigEntryAuthFailed


from pyhealthbox3.healthbox3 import (
    Healthbox3,
    Healthbox3ApiClientAuthenticationError,
    Healthbox3ApiClientError,
)

from .const import (
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL,
)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class HealthboxDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    api: Healthbox3

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: Healthbox3
    ) -> None:
        """Initialize."""

        self.hass = hass
        self.config_entry = entry
        self.host: str = entry.data[CONF_HOST]
        self.api: Healthbox3 = api

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN} - {self.host}",
            update_interval=SCAN_INTERVAL,
        )

    async def change_room_profile(
        self, room_id: int, profile_name: str
    ):
        """Start Boosting HB Room."""
        await self.api.async_change_room_profile(
            room_id=room_id, profile_name=profile_name
        )

    async def start_room_boost(
        self, room_id: int, boost_level: int, boost_timeout: int
    ):
        """Start Boosting HB Room."""
        await self.api.async_start_room_boost(
            room_id=room_id, boost_level=boost_level, boost_timeout=boost_timeout
        )

    async def stop_room_boost(self, room_id: int):
        """Stop Boosting HB Room."""
        await self.api.async_stop_room_boost(room_id=room_id)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            LOGGER.debug("Fetching Healthbox data, advanced_api_enabled=%s", self.api.advanced_api_enabled)
            await self.api.async_get_data()
            return self.api

        except Healthbox3ApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except Healthbox3ApiClientError as exception:
            raise UpdateFailed(exception) from exception
        except TypeError as exception:
            # this error occurs when library tries to access an unexpected None value
            # instead of raising and causing the integration to fail, log and return
            # the previous data so entities continue to operate with last-known values.
            LOGGER.warning(
                "Invalid data structure from Healthbox API at %s while parsing response: %s. "
                "Some sensors may not be properly connected to the device. "
                "Returning last known data and skipping this update.",
                self.host,
                exception,
            )
            # do not raise UpdateFailed; provide previous API object instead
            return self.api
        except Exception as exception:
            LOGGER.error(
                "Unexpected error fetching Healthbox data from %s: %s",
                self.host,
                exception,
                exc_info=True
            )
            raise UpdateFailed(f"Unexpected error: {exception}") from exception
