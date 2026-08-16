#!/bin/bash
SESSION="dev"

if [ -n "$TMUX" ]; then
  # Dentro de tmux → crear ventana en la sesión actual
  CURRENT=$(tmux display-message -p '#S')
  tmux new-window -n "dev" -t "$CURRENT"
  tmux split-window -h -p 25 -t "$CURRENT:dev"
  tmux split-window -v -p 15 -t "$CURRENT:dev.0"
  tmux send-keys -t "$CURRENT:dev.0" "nvim" C-m
  tmux send-keys -t "$CURRENT:dev.2" "opencode" C-m
  tmux select-pane -t "$CURRENT:dev.0"
else
  # Fuera de tmux → crear sesión nueva
  tmux kill-session -t $SESSION 2>/dev/null
  tmux new-session -d -s $SESSION
  tmux split-window -h -p 25 -t $SESSION
  tmux split-window -v -p 15 -t "$SESSION:.0"
  tmux send-keys -t "$SESSION:.0" "nvim" C-m
  tmux send-keys -t "$SESSION:.2" "opencode" C-m
  tmux select-pane -t "$SESSION:.0"
  tmux attach -t $SESSION
fi
