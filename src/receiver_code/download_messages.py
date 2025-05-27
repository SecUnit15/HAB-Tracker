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

def parse_tracking_message(message):
    """
    Parse the pipe-delimited tracking message
    Format: lat|lon|altitude|satellites|battery|temp
    """
    try:
        # Remove any surrounding quotes that might be present
        clean_message = message.strip().strip('"\'')
        
        parts = clean_message.split('|')
        if len(parts) == 6:
            return {
                'latitude': float(parts[0]),
                'longitude': float(parts[1]),
                'altitude': int(parts[2]),
                'satellites': int(parts[3]),
                'battery': float(parts[4]),
                'temperature': int(parts[5])
            }
        else:
            return {'raw_message': clean_message, 'parsed': False, 'parts_found': len(parts)}
    except Exception as e:
        return {'raw_message': message, 'error': str(e)}

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
            print(f"   📍 Location: {parsed['latitude']:.4f}, {parsed['longitude']:.4f}")
            print(f"   🏔️  Altitude: {parsed['altitude']} meters")
            print(f"   🛰️  Satellites: {parsed['satellites']}")
            print(f"   🔋 Battery: {parsed['battery']:.1f}V")
            print(f"   🌡️  Temperature: {parsed['temperature']}°F")
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
