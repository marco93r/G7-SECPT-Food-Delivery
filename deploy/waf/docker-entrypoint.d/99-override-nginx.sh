#!/bin/sh
set -eu

echo "99-override-nginx: applying custom nginx config"

# Make sure our custom configuration replaces the template-generated files
install -m 0644 /opt/custom/nginx.conf /etc/nginx/nginx.conf

# The default template adds an SSL server we don't need; drop it to avoid warnings
rm -f /etc/nginx/conf.d/default.conf
