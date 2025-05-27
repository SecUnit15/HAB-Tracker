This code uses Google Cloud Functions and sets up a receiver to receive POST messages from the Rockblock Ground Control service, and to store them in JSON format to a bucket. You'll need to update deploy_function.sh with the Google Cloud region and unique bucket name that you want to use.

To make your own bucket: 
`gsutil mb gs://[your bucket name here]`

After running deploy_function.sh shell script and deploying the cloud assets, run:
`uv run download_messages.py`

The output should look something like this:

📨 Message #8
   IMEI: 30143**********
   Timestamp: 2025-05-26T18:26:58.865694
   File: 30143**********_2025-05-26T18:26:58.865694.json
   Raw Message: "32.8000|-117.1000|150|8|3.7|72"
   📍 Location: 32.8000, -117.1000
   🏔️  Altitude: 150 meters
   🛰️  Satellites: 8
   🔋 Battery: 3.7V
   🌡️  Temperature: 72°F

