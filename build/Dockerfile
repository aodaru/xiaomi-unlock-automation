FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server tmux iputils-ping ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir requests ntplib pytz urllib3 icmplib colorama \
    && mkdir -p /run/sshd /app \
    && chmod 0755 /run/sshd

COPY SCRIPT_PERMISO_DESBLOQUEO.py /app/SCRIPT_PERMISO_DESBLOQUEO.py
COPY build/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY build/.config/tmux /opt/tmux-config/.config/tmux

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

WORKDIR /app
EXPOSE 22

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
