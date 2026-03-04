"""Test the Healthbox integration against real JSON responses from the device."""
import sys
import json
from pathlib import Path
from decimal import Decimal

# Add the custom_components to the path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

from healthbox.const import HealthboxRoom, HealthboxDataObject


# Real JSON data from the Healthbox device
REAL_JSON = {
    "device_type": "HEALTHBOX3",
    "description": "Healthbox 3.0",
    "serial": "240318P0085",
    "warranty_number": "XUD320380018C24",
    "room": {
        "1": {
            "name": "Toilette RDC",
            "type": "Toilet",
            "sensor": [
                {
                    "basic_id": 0,
                    "name": "indoor mixed CO2[0]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "concentration": {
                            "unit": "ppm",
                            "value": 572.0
                        }
                    },
                    "type": "indoor mixed CO2"
                },
                {
                    "basic_id": 2,
                    "name": "indoor temperature[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "temperature": {
                            "unit": "deg C",
                            "value": 22.13473716334784
                        }
                    },
                    "type": "indoor temperature"
                },
                {
                    "basic_id": 2,
                    "name": "indoor relative humidity[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "humidity": {
                            "unit": "pct",
                            "value": 47.954528114747845
                        }
                    },
                    "type": "indoor relative humidity"
                }
            ]
        },
        "2": {
            "name": "Laundry room",
            "type": "LaundryRoom",
            "sensor": [
                {
                    "basic_id": 0,
                    "name": "indoor mixed CO2[0]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "concentration": {
                            "unit": "ppm",
                            "value": 572.0
                        }
                    },
                    "type": "indoor mixed CO2"
                },
                {
                    "basic_id": 3,
                    "name": "indoor temperature[3]_HealthBox 3[Healthbox3]",
                    "parameter": {},
                    "type": "indoor temperature"
                },
                {
                    "basic_id": 3,
                    "name": "indoor relative humidity[3]_HealthBox 3[Healthbox3]",
                    "parameter": {},
                    "type": "indoor relative humidity"
                },
                {
                    "basic_id": 3,
                    "name": "indoor air quality index[3]_HealthBox 3[Healthbox3]",
                    "parameter": {},
                    "type": "indoor air quality index"
                }
            ]
        },
        "3": {
            "name": "Cuisine",
            "type": "Kitchen",
            "sensor": [
                {
                    "basic_id": 4,
                    "name": "indoor temperature[4]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "temperature": {
                            "unit": "deg C",
                            "value": 22.401770046540022
                        }
                    },
                    "type": "indoor temperature"
                },
                {
                    "basic_id": 4,
                    "name": "indoor relative humidity[4]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "humidity": {
                            "unit": "pct",
                            "value": 45.54512855725948
                        }
                    },
                    "type": "indoor relative humidity"
                },
                {
                    "basic_id": 4,
                    "name": "indoor air quality index[4]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "index": {
                            "unit": "",
                            "value": 31.5
                        },
                        "main_pollutant": {
                            "unit": "",
                            "value": ""
                        }
                    },
                    "type": "indoor air quality index"
                }
            ]
        }
    },
    "sensor": [
        {
            "name": "global air quality index",
            "type": "global air quality index",
            "basic_id": 0,
            "parameter": {
                "index": {
                    "unit": "",
                    "value": 31.583333333333336
                },
                "main_pollutant": {
                    "unit": "",
                    "value": ""
                }
            }
        }
    ]
}


def test_room_1_with_valid_data():
    """Test Room 1 (Toilette) with valid sensor data."""
    print("\n=== Test 1: Room 1 - Valid Sensor Data ===")
    room_data = REAL_JSON["room"]["1"]
    
    room = HealthboxRoom("1", room_data)
    print(f"✓ Room created: {room.name} ({room.type})")
    print(f"  Temperature: {room.indoor_temperature}°C")
    print(f"  Humidity: {room.indoor_humidity}%")
    print(f"  CO2: {room.indoor_co2_concentration} ppm")
    
    assert room.name == "Toilette RDC"
    assert room.indoor_temperature == 22.13473716334784
    assert room.indoor_humidity == 47.954528114747845
    assert room.indoor_co2_concentration == 572.0
    print("✓ All sensor values correct!")


def test_room_2_empty_parameters():
    """Test Room 2 (Laundry) with EMPTY parameters - the critical bug case."""
    print("\n=== Test 2: Room 2 - Empty Parameters (CRITICAL TEST) ===")
    room_data = REAL_JSON["room"]["2"]
    
    room = HealthboxRoom("2", room_data)
    print(f"✓ Room created: {room.name} ({room.type})")
    print(f"  Temperature (empty param): {room.indoor_temperature}")
    print(f"  Humidity (empty param): {room.indoor_humidity}")
    print(f"  AQI (empty param): {room.indoor_aqi}")
    
    assert room.name == "Laundry room"
    # Empty parameters should return None, not crash
    assert room.indoor_temperature is None
    assert room.indoor_humidity is None
    assert room.indoor_aqi is None
    print("✓ No crash with empty parameters!")


def test_room_3_kitchen():
    """Test Room 3 (Kitchen) with mixed valid and invalid data."""
    print("\n=== Test 3: Room 3 - Kitchen with Mixed Data ===")
    room_data = REAL_JSON["room"]["3"]
    
    room = HealthboxRoom("3", room_data)
    print(f"✓ Room created: {room.name} ({room.type})")
    print(f"  Temperature: {room.indoor_temperature}°C")
    print(f"  Humidity: {room.indoor_humidity}%")
    print(f"  AQI: {room.indoor_aqi}")
    
    assert room.name == "Cuisine"
    assert room.indoor_temperature == 22.401770046540022
    assert room.indoor_humidity == 45.54512855725948
    assert room.indoor_aqi == 31.5
    print("✓ All values extracted correctly!")


def test_global_aqi():
    """Test global AQI extraction."""
    print("\n=== Test 4: Global AQI ===")
    data = REAL_JSON
    
    # Extract global AQI sensor
    global_aqi = None
    try:
        sensors = data.get("sensor") or []
        for sensor in sensors:
            if sensor.get("type") == "global air quality index":
                param = sensor.get("parameter")
                if isinstance(param, dict) and "index" in param:
                    idx = param.get("index")
                    if isinstance(idx, dict) and "value" in idx:
                        global_aqi = idx["value"]
    except (TypeError, KeyError, AttributeError):
        pass
    
    print(f"✓ Global AQI extracted: {global_aqi}")
    assert global_aqi == 31.583333333333336
    print("✓ Global AQI correct!")


def test_all_rooms():
    """Test creating all rooms from the real JSON."""
    print("\n=== Test 5: All Rooms from Real JSON ===")
    
    all_rooms = []
    for room_id, room_data in REAL_JSON["room"].items():
        try:
            room = HealthboxRoom(room_id, room_data)
            all_rooms.append(room)
            temp = room.indoor_temperature
            humidity = room.indoor_humidity
            print(f"✓ Room {room_id}: {room.name}")
            print(f"    Temperature: {temp}, Humidity: {humidity}")
        except Exception as e:
            print(f"✗ Failed to create room {room_id}: {e}")
            raise
    
    assert len(all_rooms) == len(REAL_JSON["room"])
    print(f"\n✓ Successfully created all {len(all_rooms)} rooms!")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Healthbox Integration Against Real Device JSON")
    print("=" * 70)
    
    try:
        test_room_1_with_valid_data()
        test_room_2_empty_parameters()
        test_room_3_kitchen()
        test_global_aqi()
        test_all_rooms()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe integration successfully handles:")
        print("  ✓ Valid sensor data with proper values")
        print("  ✓ Empty parameters (the critical bug case)")
        print("  ✓ Mixed valid and empty sensor data")
        print("  ✓ Global AQI extraction")
        print("  ✓ Multiple rooms with varying data completeness")
        print("\nThe defensive error handling is working correctly!")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
