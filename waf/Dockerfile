FROM owasp/modsecurity-crs:nginx

# ensure we can install packages during build
USER root

# Generate self-signed cert for HTTPS termination at WAF
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssl \
 && mkdir -p /etc/nginx/certs \
 && openssl req -x509 -nodes -newkey rsa:2048 \
      -keyout /etc/nginx/certs/server.key \
      -out /etc/nginx/certs/server.crt \
      -subj "/CN=localhost" -days 365 \
 && rm -rf /var/lib/apt/lists/*

COPY nginx.conf /etc/nginx/templates/nginx.conf.template
COPY include.conf /etc/nginx/modsecurity.d/include.conf
