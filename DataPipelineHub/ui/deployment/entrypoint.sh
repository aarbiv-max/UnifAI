#!/bin/sh
export DOLLAR='$'
if [ -n "$MODULE_VERSION" ]; then
  echo "window.__MODULE_VERSION__='$MODULE_VERSION';" > /usr/share/nginx/html/version.js
fi
envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'