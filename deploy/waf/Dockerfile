FROM owasp/modsecurity-crs:nginx

# Provide custom templates so the entrypoint can render them at runtime.
COPY nginx.conf /etc/nginx/templates/nginx.conf.template

# CRS legt crs-setup.conf und Rules bereits im Image ab, daher reicht es,
# unsere zusätzliche Konfiguration in das Template-Verzeichnis zu kopieren.
COPY modsecurity.conf /etc/nginx/templates/modsecurity.d/modsecurity.conf.template
