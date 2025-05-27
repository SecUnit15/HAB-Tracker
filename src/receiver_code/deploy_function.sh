# Update to use your own bucket name!
gcloud functions deploy rockblock-receiver \
  --gen2 \
  --runtime python310 \
  --region us-central1 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars BUCKET_NAME=hab-tracker-424242 \
  --entry-point rockblock_receiver \
  --source=.

