# Dashboard Setup Guide

This guide shows how to create a dashboard with controls for Healthbox room boost functionality.

## Step 1: Create Two Slider Helpers

Go to **Settings → Devices & services → Helpers → Create helper → Number**

### Create Boost Level Helper
- **Entity ID**: `input_number.sdb_boost_level`
- **Min**: 1
- **Max**: 100
- **Step**: 1
- **Unit of measurement**: %
- **Mode**: Slider

### Create Boost Timeout Helper
- **Entity ID**: `input_number.sdb_boost_timeout`
- **Min**: 5
- **Max**: 720
- **Step**: 5 (or 1)
- **Unit of measurement**: min
- **Mode**: Slider

## Step 2: Create a Script

Go to **Settings → Automations & scenes → Scripts → Create script**

Choose **Edit in YAML** and paste the following:

```yaml
alias: Start SDB room boost
mode: single
sequence:
  - action: healthbox.start_room_boost
    data:
      device_id: "dcd20c575972a426358c4c8fdd504b20"
      boost_level: "{{ states('input_number.sdb_boost_level') | int(0) }}"
      boost_timeout: "{{ states('input_number.sdb_boost_timeout') | int(0) }}"
```

**Important**: Replace `device_id` with the actual device ID of your Healthbox room.

Save the script (it will be assigned an entity ID like `script.start_sdb_room_boost`).

## Step 3: Add Controls to Dashboard

Go to your dashboard and add an **Entities** card with:

```yaml
type: entities
entities:
  - entity: input_number.sdb_boost_level
    name: Boost level (%)
  - entity: input_number.sdb_boost_timeout
    name: Boost timeout (min)
  - type: button
    name: Start boost
    tap_action:
      action: call-service
      service: script.start_sdb_room_boost
```

## Step 4: Test

1. Move the two sliders to your desired values
2. Press **Start boost** button
3. The script reads the slider values and calls `healthbox.start_room_boost` with:
   - `boost_level` = 1–100 (%)
   - `boost_timeout` = 5–720 (minutes)

## Troubleshooting

**Script entity ID mismatch**: If your script entity ID is not exactly `script.start_sdb_room_boost`, replace the `service` line in the dashboard button with your script's actual entity ID shown in the script editor.

**Device ID not found**: Make sure to replace the example `device_id` in the script with the actual device ID of your Healthbox room. You can find this in the device settings.
