import os
import pandas as pd
import meraki
from meraki.exceptions import APIError

# --- CONFIGURATION ---
API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY") or "YOUR_API_KEY_HERE"
SWITCH_SERIAL = "YOUR_SWITCH_SERIAL_HERE"  # Format: XXXX-XXXX-XXXX
CSV_FILE = "port_config.csv"
# ---------------------

def main():
    # Initialize the Meraki dashboard session
    dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True)
    
    # Load and clean the CSV data
    try:
        df = pd.read_csv(CSV_FILE)
        # Fill NaN values with appropriate defaults so the API doesn't choke
        df = df.where(pd.notnull(df), None)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return

    print(f"🚀 Starting configuration for Switch {SWITCH_SERIAL}...")
    print(f"📋 Loaded {len(df)} port configurations from {CSV_FILE}.\n")

    # Iterate through each row in the CSV
    for index, row in df.iterrows():
        port_id = str(row['port_id'])
        
        # Construct the payload dynamically based on CSV columns
        payload = {
            "name": row['name'],
            "enabled": bool(row['enabled']) if row['enabled'] is not None else True,
            "type": row['type'] if row['type'] else "access",
        }
        
        # Handle tags (convert semicolon-separated string to list)
        if row['tags']:
            payload["tags"] = [t.strip() for t in str(row['tags']).split(';')]
        else:
            payload["tags"] = []

        # VLAN configurations depend on port type
        if payload["type"] == "access" and row['vlan']:
            payload["vlan"] = int(row['vlan'])
            if row['voice_vlan']:
                payload["voiceVlan"] = int(row['voice_vlan'])
        elif payload["type"] == "trunk":
            # If trunk, default allowed VLANs to 'all' unless specified, or map a native vlan
            payload["vlan"] = int(row['vlan']) if row['vlan'] else 1
            payload["allowedVlans"] = "all"

        # PoE setting
        if row['poe_enabled'] is not None:
            payload["poeEnabled"] = bool(row['poe_enabled'])

        # Filter out None values to keep the payload clean
        payload = {k: v for k, v in payload.items() if v is not None}

        # Update the port
        try:
            print(f"🔄 Updating Port {port_id}...", end="", flush=True)
            
            dashboard.switch.updateDeviceSwitchPort(
                serial=SWITCH_SERIAL,
                portId=port_id,
                **payload
            )
            
            print(f" ✅ Success ({payload.get('name', 'No Name')})")
            
        except APIError as e:
            print(f" ❌ Failed! Error: {e.message}")
        except Exception as e:
            print(f" ❌ Unexpected error on port {port_id}: {e}")

    print("\n🎉 Bulk port configuration complete.")

if __name__ == "__main__":
    main()