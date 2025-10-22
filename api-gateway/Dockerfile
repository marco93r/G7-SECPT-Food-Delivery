FROM nginx:1.27-alpine
# Use template so env vars (e.g., API_KEY) are substituted at runtime
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 8080
