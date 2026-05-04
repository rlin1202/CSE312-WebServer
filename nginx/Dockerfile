FROM nginx

COPY ./nginx/cert.pem /etc/nginx/cert.pem
COPY ./nginx/private.key /etc/nginx/private.key
COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf
COPY ./public /usr/share/nginx/html/public