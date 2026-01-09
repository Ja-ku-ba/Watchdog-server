#!/bin/bash
# inside crontab -e coppy line blow
# @reboot /var/www/Watchdog-server/start_face_detector.sh
cd /var/www/Watchdog-server
/var/www/Watchdog-server/.venv/bin/python -m workers.face_detector >> /var/log/cron/face_detector.log 2>&1
