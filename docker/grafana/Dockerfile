FROM grafana/grafana:11.0.0

USER root

COPY grafana.ini /etc/grafana/grafana.ini
COPY signal-theme.css /usr/share/grafana/public/signal-theme.css

RUN sed -i 's|</head>|<link rel="stylesheet" href="/public/signal-theme.css" /></head>|' \
    /usr/share/grafana/public/views/index.html

USER grafana