#!/bin/bash
output=$(curl https://www.time.ir/fa/event/list/1/$(date +"%Y/%m/%d") | grep 'eventHoliday')
[ -z "$output" ] && /usr/bin/python3.9 /opt/patogh_telegram_bot-master/manage.py notifyclasses >> /var/log/notify-users.log 2>&1
