FROM node:22-alpine AS build
WORKDIR /srv/web
COPY package.json ./
RUN npm install --no-fund --no-audit
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /srv/web/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
