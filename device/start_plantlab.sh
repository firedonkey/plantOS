#!/bin/bash

cd ~/projects/plantOS/device
source ../.venv/bin/activate

python platform_client.py \
  --platform-url https://plantlab-api-418533861080.us-central1.run.app \
  --config data/provisioning/device_config.json \
  --send-interval 10 \
  --command-interval 1 \
  --image-every 1