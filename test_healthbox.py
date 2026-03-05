#!/usr/bin/env python3
"""Test script for Healthbox integration.

Run this script with your Healthbox IP and API key:
    python test_healthbox.py --host 192.168.0.55 --api-key YOUR_API_KEY

Or set environment variables:
    export HEALTHBOX_HOST=192.168.0.55
    export HEALTHBOX_API_KEY=YOUR_API_KEY
    python test_healthbox.py
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add the custom_components to the path so we can import the library
sys.path.insert(0, str(Path(__file__).parent / "custom_components" / "healthbox" / "lib"))

from pyhealthbox3.healthbox3 import Healthbox3
from aiohttp import ClientSession
import contextlib


async def test_healthbox(host: str, api_key: str | None = None):
    """Test the Healthbox connection and sensor reading."""

    async with ClientSession() as session:
        api = Healthbox3(host=host, api_key=api_key, session=session)

        # Step 1: Test connectivity and get raw data
        try:
            raw_data = await api.request(method="GET", endpoint="/v2/api/data/current")
            if isinstance(raw_data, dict):
                for key in raw_data:
                    val = raw_data[key]
                    if isinstance(val, dict | list):
                        pass
                    else:
                        pass
        except Exception:
            return False

        # Step 2: Enable advanced features if API key provided
        if api_key:
            with contextlib.suppress(Exception):
                await api.async_enable_advanced_api_features()

        # Step 3: Fetch data
        try:
            await api.async_get_data()
        except Exception:
            import traceback
            traceback.print_exc()
            return False

        # Step 4: Display device info

        # Step 5: Display room data

        all_success = True
        for room in api.rooms:

            # Try to read each sensor
            sensors = {
                'Temperature': ('indoor_temperature', '°C'),
                'Humidity': ('indoor_humidity', '%'),
                'CO2': ('indoor_co2_concentration', 'ppm'),
                'AQI': ('indoor_aqi', 'index'),
                'VOC (ppm)': ('indoor_voc_ppm', 'ppm'),
                'VOC (µg/m³)': ('indoor_voc_microg_per_cubic', 'µg/m³'),
                'Airflow': ('airflow_ventilation_rate', '%'),
            }

            for _sensor_name, (prop_name, _unit) in sensors.items():
                try:
                    value = getattr(room, prop_name, None)
                    if value is not None:
                        pass
                    else:
                        pass
                except Exception:
                    all_success = False

            # Boost status
            if room.boost:
                pass

        if all_success:
            pass
        else:
            pass

        return all_success


async def main():
    """Run main test sequence."""
    parser = argparse.ArgumentParser(
        description="Test Healthbox integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_healthbox.py --host 192.168.0.55
  python test_healthbox.py --host 192.168.0.55 --api-key YOUR_KEY
  HEALTHBOX_HOST=192.168.0.55 HEALTHBOX_API_KEY=key python test_healthbox.py
        """
    )
    parser.add_argument('--host', help='Healthbox IP address')
    parser.add_argument('--api-key', help='Healthbox API key (optional)')

    args = parser.parse_args()

    # Get host from args or environment
    host = args.host or os.getenv('HEALTHBOX_HOST')
    if not host:
        parser.print_help()
        return False

    # Get API key from args or environment
    api_key = args.api_key or os.getenv('HEALTHBOX_API_KEY')

    success = await test_healthbox(host, api_key)
    return success


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
