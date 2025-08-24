FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./

RUN npm install --omit=dev

COPY src/ ./src/
COPY public/ ./public/
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY tsconfig.json ./

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
