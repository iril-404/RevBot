#!/bin/bash
sudo fuser -k 5000/tcp
# /usr/bin/python3 -m gunicorn --bind 0.0.0.0:5000 -w 8 webhook:app
/usr/bin/python3 /mnt/SHARE/cict_proj/99_Tools/RevBotV2/tools/webhook.py