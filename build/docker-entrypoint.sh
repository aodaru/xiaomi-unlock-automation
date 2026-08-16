#!/bin/sh
set -eu

: "${SSH_USER:=operator}"
: "${SSH_PASSWORD:?SSH_PASSWORD debe estar definido en .env}"

case "$SSH_USER" in
  ''|*[!a-zA-Z0-9_-]*)
    echo "SSH_USER solo puede contener letras, números, guion y guion bajo" >&2
    exit 1
    ;;
esac

if ! id "$SSH_USER" >/dev/null 2>&1; then
  if getent group "$SSH_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --gid "$SSH_USER" "$SSH_USER"
  else
    useradd --create-home --shell /bin/bash "$SSH_USER"
  fi
fi

mkdir -p "/home/$SSH_USER/.config" 
cp -a /opt/tmux-config/.config/tmux "/home/$SSH_USER/.config/"
mkdir -p "/home/$SSH_USER/.config/omarchy/current/theme"
touch "/home/$SSH_USER/.config/omarchy/current/theme/tmux-theme.conf"
chown -R "$SSH_USER:$SSH_USER" "/home/$SSH_USER/.config"

printf '%s:%s\n' "$SSH_USER" "$SSH_PASSWORD" | chpasswd

sed -i \
  -e 's/^#\?PasswordAuthentication .*/PasswordAuthentication yes/' \
  -e 's/^#\?KbdInteractiveAuthentication .*/KbdInteractiveAuthentication no/' \
  -e 's/^#\?UsePAM .*/UsePAM no/' \
  /etc/ssh/sshd_config

ssh-keygen -A
exec /usr/sbin/sshd -D -e
