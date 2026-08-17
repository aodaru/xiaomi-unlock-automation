#!/bin/sh
set -eu

: "${SSH_USER:=operator}"
: "${SSH_AUTHORIZED_KEYS_FILE:=/run/secrets/authorized_keys}"

case "$SSH_USER" in
  ''|*[!a-zA-Z0-9_-]*)
    echo "SSH_USER solo puede contener letras, números, guion y guion bajo" >&2
    exit 1
    ;;
esac

if ! id "$SSH_USER" >/dev/null 2>&1; then
  echo "el usuario SSH no existe en la imagen" >&2
  exit 1
fi

if [ ! -s "$SSH_AUTHORIZED_KEYS_FILE" ]; then
  echo "falta un archivo de claves SSH no vacío" >&2
  exit 1
fi

mkdir -p "/home/$SSH_USER/.ssh" /workspace/jobs /workspace/videos
install -m 0600 "$SSH_AUTHORIZED_KEYS_FILE" "/home/$SSH_USER/.ssh/authorized_keys"
chown -R "$SSH_USER:$SSH_USER" "/home/$SSH_USER/.ssh"

sed -i \
  -e 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' \
  -e 's/^#\?KbdInteractiveAuthentication .*/KbdInteractiveAuthentication no/' \
  -e 's/^#\?ChallengeResponseAuthentication .*/ChallengeResponseAuthentication no/' \
  -e 's/^#\?UsePAM .*/UsePAM no/' \
  -e 's/^#\?PermitRootLogin .*/PermitRootLogin no/' \
  /etc/ssh/sshd_config

printf '\nAllowUsers %s\nPubkeyAuthentication yes\nAuthorizedKeysFile .ssh/authorized_keys\n' "$SSH_USER" >> /etc/ssh/sshd_config

ssh-keygen -A
exec /usr/sbin/sshd -D -e
