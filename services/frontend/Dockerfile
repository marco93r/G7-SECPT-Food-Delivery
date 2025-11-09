FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_ORDER_API=http://order-service:8081
ARG VITE_RESTAURANT_API=http://restaurant-service:8082
ARG VITE_API_TOKEN=

ENV VITE_ORDER_API=$VITE_ORDER_API \
    VITE_RESTAURANT_API=$VITE_RESTAURANT_API \
    VITE_API_TOKEN=$VITE_API_TOKEN

COPY services/frontend/package*.json ./
RUN npm install

COPY services/frontend .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY services/frontend/nginx.conf /etc/nginx/nginx.conf
COPY deploy/waf/certs /etc/nginx/certs
RUN chmod 600 /etc/nginx/certs/*.key

EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
