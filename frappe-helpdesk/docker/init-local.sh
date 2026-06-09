#!/bin/bash
set -e

if [ "$(id -u)" = "0" ]; then
    mkdir -p /workspace/desk/node_modules /home/frappe/.cache/yarn
    ln -sfn /home/frappe/frappe-bench/sites /sites
    chown frappe:frappe /home/frappe/.cache /home/frappe/.cache/yarn
    chown -R frappe:frappe /workspace/desk/node_modules
    exec su frappe -c "bash /workspace/docker/init-local.sh"
fi

if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, starting services"
    cd /home/frappe/frappe-bench
    bench start
    exit 0
fi

if [ -d "/home/frappe/frappe-bench" ]; then
    echo "Removing incomplete bench directory"
    rm -rf /home/frappe/frappe-bench
fi

echo "Creating new bench..."
bench init --skip-redis-config-generation frappe-bench --version version-15

cd /home/frappe/frappe-bench

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app telephony
ln -s /workspace apps/helpdesk
/home/frappe/frappe-bench/env/bin/pip install -e apps/helpdesk
cd apps/helpdesk/desk
yarn install --check-files
cd /home/frappe/frappe-bench
printf '%s\n' frappe telephony helpdesk > sites/apps.txt

bench new-site helpdesk.localhost \
    --force \
    --mariadb-root-password 123 \
    --admin-password admin \
    --no-mariadb-socket

bench --site helpdesk.localhost install-app telephony
bench --site helpdesk.localhost install-app helpdesk
bench --site helpdesk.localhost set-config developer_mode 1
bench --site helpdesk.localhost set-config mute_emails 1
bench --site helpdesk.localhost set-config server_script_enabled 1
bench --site helpdesk.localhost clear-cache
bench use helpdesk.localhost
bench build --app helpdesk

bench start
