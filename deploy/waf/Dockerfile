FROM owasp/modsecurity-crs:nginx

USER root

RUN mkdir -p /opt/custom

COPY nginx.conf /opt/custom/nginx.conf
COPY certs /opt/custom/certs
COPY docker-entrypoint.d/99-override-nginx.sh /docker-entrypoint.d/99-override-nginx.sh

# Ensure runtime scripts can manage configs without permission issues
RUN chmod +x /docker-entrypoint.d/99-override-nginx.sh \
    && chmod 600 /opt/custom/certs/*.key
