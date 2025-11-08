FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_ORDER_API=http://order-service:8081
ARG VITE_RESTAURANT_API=http://restaurant-service:8082

ENV VITE_ORDER_API=$VITE_ORDER_API \
    VITE_RESTAURANT_API=$VITE_RESTAURANT_API

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
