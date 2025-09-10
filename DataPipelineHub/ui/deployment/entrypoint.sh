#!/bin/sh
export DOLLAR='$'
envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
if [ -f /usr/share/nginx/html/version.js.template ]; then
    envsubst < /usr/share/nginx/html/version.js.template > /usr/share/nginx/html/version.js
    echo "Generated version.js with MODULE_VERSION=$MODULE_VERSION"
else
    echo "version.js.template not found, skipping..."
fi

exec nginx -g 'daemon off;'