#!/usr/bin/env python3
"""
Download and parse RockBLOCK messages from Google Cloud Storage
"""

import json
import os
from datetime import datetime
from google.cloud import storage

# Configuration
BUCKET_NAME = "hab-tracker-424242"
YOUR_IMEI = "301434061666900"  # Your RockBLOCK IMEI

def download_messages(bucket_name, imei_filter=None, limit=10):
    """
    Download recent messages from Google Cloud Storage bucket
    
    Args:
        bucket_name: GCS bucket name
        imei_filter: Only show messages from this IMEI (optional)
        limit: Maximum number of messages to show
    """
    try:
        # Initialize storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        print(f"🔍 Searching bucket '{bucket_name}' for messages...")
        
        # List all blobs (files) in the bucket
        blobs = bucket.list_blobs()
        
        messages = []
        
        for blob in blobs:
            # Skip if filtering by IMEI and this doesn't match
            if imei_filter and not blob.name.startswith(imei_filter):
                continue
                
            try:
                # Download and parse the JSON file
                content = blob.download_as_text()
                message_data = json.loads(content)
                
                # Add blob name and creation time for reference
                message_data['blob_name'] = blob.name
                message_data['blob_created'] = blob.time_created.isoformat() if blob.time_created else None
                
                messages.append(message_data)
                
            except Exception as e:
                print(f"⚠️  Error parsing {blob.name}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Limit results
        if limit:
            messages = messages[:limit]
        
        return messages
        
    except Exception as e:
        print(f"❌ Error accessing bucket: {e}")
        print("Make sure you have Google Cloud credentials set up:")
        print("  gcloud auth application-default login")
        return []

def _field(text, convert):
    """Read one field, or None if the payload sent '?' for it."""
    if text == '?':
        return None
    return convert(text)


def parse_tracking_message(message):
    """
    Parse the pipe-delimited tracking message
    Format: H2|boot|seq|lat|lon|altitude|satellites|battery|temp|fix_age
    """
    try:
        # Remove any surrounding quotes that might be present
        clean_message = message.strip().strip('"\'')

        parts = clean_message.split('|')
        if parts[0] == 'H2' and len(parts) == 10:
            return {
                'boot_id': _field(parts[1], int),
                'sequence': _field(parts[2], int),
                'latitude': _field(parts[3], float),
                'longitude': _field(parts[4], float),
                'altitude': _field(parts[5], int),
                'satellites': _field(parts[6], int),
                'battery': _field(parts[7], float),
                'temperature': _field(parts[8], int),
                'fix_age': _field(parts[9], int),
            }
        else:
            return {'raw_message': clean_message, 'parsed': False, 'parts_found': len(parts)}
    except Exception as e:
        return {'raw_message': message, 'error': str(e)}

def _show(value, style="%d"):
    """Format a reading for display, or '?' if the payload did not have it."""
    if value is None:
        return "?"
    return style % value


def display_messages(messages):
    """Display messages in a nice format"""
    
    if not messages:
        print("📭 No messages found")
        return
    
    print(f"\n📡 Found {len(messages)} messages:")
    print("=" * 80)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n📨 Message #{i}")
        print(f"   IMEI: {msg.get('imei', 'Unknown')}")
        print(f"   Timestamp: {msg.get('timestamp', 'Unknown')}")
        print(f"   File: {msg.get('blob_name', 'Unknown')}")
        
        # Parse the tracking data
        raw_message = msg.get('message', '')
        parsed = parse_tracking_message(raw_message)
        
        print(f"   Raw Message: {raw_message}")
        
        if 'latitude' in parsed:
            print(f"   🔢 Boot: {_show(parsed['boot_id'])}"
                  f"  Seq: {_show(parsed['sequence'])}"
                  f"  Fix age: {_show(parsed['fix_age'])}s")
            print(f"   📍 Location: {_show(parsed['latitude'], '%.4f')},"
                  f" {_show(parsed['longitude'], '%.4f')}")
            print(f"   🏔️  Altitude: {_show(parsed['altitude'])} meters")
            print(f"   🛰️  Satellites: {_show(parsed['satellites'])}")
            print(f"   🔋 Battery: {_show(parsed['battery'], '%.2f')}V")
            print(f"   🌡️  Temperature: {_show(parsed['temperature'])}°F")
        elif 'error' in parsed:
            print(f"   ⚠️  Parse Error: {parsed['error']}")
        else:
            print(f"   ⚠️  Could not parse message")

def main():
    """Main function"""
    print("🚀 RockBLOCK Message Downloader")
    print("=" * 40)
    
    # Download messages from your device only
    print(f"Looking for messages from IMEI: {YOUR_IMEI}")
    messages = download_messages(BUCKET_NAME, imei_filter=YOUR_IMEI, limit=10)
    
    # Display results
    display_messages(messages)

if __name__ == "__main__":
    main()
