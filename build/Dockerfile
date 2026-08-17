FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg openssh-server tmux ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd /app /workspace/jobs /workspace/videos /usr/local/lib/video-tool \
    && chmod 0755 /run/sshd

COPY build/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY SCRIPT_PERMISO_DESBLOQUEO.py /app/SCRIPT_PERMISO_DESBLOQUEO.py
COPY build/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY build/video-tool.py build/video-tool build/probe build/prepare_video build/extract_audio \
     build/mix_audio build/export_reel /usr/local/lib/video-tool/

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh /usr/local/lib/video-tool/* \
      && id operator >/dev/null 2>&1 && userdel operator || true \
      && getent group operator >/dev/null && groupdel operator || true \
      && groupadd -g 568 operator \
      && useradd -u 568 -g operator --create-home --shell /bin/bash operator \
      && usermod --unlock operator && passwd -d operator \
      && chown -R operator:operator /app /workspace

WORKDIR /app

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
