FROM python:3.13-alpine AS build
WORKDIR /app
COPY website/ website/
RUN python3 -B website/build.py && python3 -B website/check.py

FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY --from=build /app/website/dist/ /usr/share/nginx/html/
COPY --from=build /app/website/csp-header.conf /etc/nginx/snippets/csp-header.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
USER 101:101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
