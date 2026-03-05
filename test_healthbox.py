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


async def test_healthbox(host: str, api_key: str | None = None):
    """Test the Healthbox connection and sensor reading."""
    print(f"\n{'='*60}")
    print(f"Testing Healthbox at {host}")
    print(f"API Key: {'Provided' if api_key else 'Not provided'}")
    print(f"{'='*60}\n")

    async with ClientSession() as session:
        api = Healthbox3(host=host, api_key=api_key, session=session)

        # Step 1: Test connectivity and get raw data
        print("1. Testing connectivity and dumping raw JSON...")
        try:
            raw_data = await api.request(method="GET", endpoint="/v2/api/data/current")
            print("   ✓ Raw data fetched successfully\n")
            print("   Raw JSON structure:")
            print(f"   Top-level keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
            if isinstance(raw_data, dict):
                for key in raw_data:
                    val = raw_data[key]
                    if isinstance(val, (dict, list)):
                        print(f"      {key}: {type(val).__name__} with {len(val)} items")
                    else:
                        print(f"      {key}: {type(val).__name__} = {val}")
            print()
        except Exception as e:
            print(f"   ✗ Failed to fetch raw data: {e}\n")
            return False

        # Step 2: Enable advanced features if API key provided
        if api_key:
            print("2. Enabling advanced API features...")
            try:
                await api.async_enable_advanced_api_features()
                print(f"   ✓ Advanced API enabled: {api.advanced_api_enabled}\n")
            except Exception as e:
                print(f"   ✗ Failed to enable advanced API: {e}\n")
                print("   (Continuing anyway, sensors should still work)\n")

        # Step 3: Fetch data
        print("3. Fetching data from /v2/api/data/current...")
        try:
            await api.async_get_data()
            print("   ✓ Data fetched successfully\n")
        except Exception as e:
            print(f"   ✗ Failed to fetch data: {e}")
            print("\n   Full traceback:")
            import traceback
            traceback.print_exc()
            print()
            return False

        # Step 4: Display device info
        print("4. Device Information:")
        print(f"   Serial: {api.serial}")
        print(f"   Firmware: {api.firmware_version}")
        print(f"   Description: {api.description}")
        print(f"   Global AQI: {api.global_aqi}")
        print(f"   WiFi Status: {api.wifi.status if api.wifi else 'N/A'}\n")

        # Step 5: Display room data
        print(f"5. Rooms ({len(api.rooms)} found):")
        print(f"   {'-'*56}")

        all_success = True
        for room in api.rooms:
            print(f"\n   Room: {room.name} (ID: {room.room_id})")
            print(f"   Type: {room.type}")
            print(f"   Profile: {room.profile_name}")
            print(f"   Enabled Sensors: {room.enabled_sensors}")

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

            print("\n   Sensor Values:")
            for sensor_name, (prop_name, unit) in sensors.items():
                try:
                    value = getattr(room, prop_name, None)
                    if value is not None:
                        print(f"      {sensor_name:20} {value:10.2f} {unit}")
                    else:
                        print(f"      {sensor_name:20} <None>")
                except Exception as e:
                    print(f"      {sensor_name:20} ERROR: {e}")
                    all_success = False

            # Boost status
            print("\n   Boost Status:")
            if room.boost:
                print(f"      Enabled: {room.boost.enabled}")
                print(f"      Level: {room.boost.level}")
                print(f"      Remaining: {room.boost.remaining}s")

        print(f"\n{'='*60}")
        if all_success:
            print("✓ Test completed successfully!")
        else:
            print("⚠ Test completed with some errors (see above)")
        print(f"{'='*60}\n")

        return all_success


async def main():
    """Main entry point."""
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
        print("Error: Please provide --host or set HEALTHBOX_HOST environment variable")
        parser.print_help()
        return False

    # Get API key from args or environment
    api_key = args.api_key or os.getenv('HEALTHBOX_API_KEY')

    success = await test_healthbox(host, api_key)
    return success


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
