#!/usr/bin/env bash
# Standard startup path for this project. The next session reaches a working
# state by reading PROGRESS.md and running this script. If it can't, the last
# session didn't finish.
set -euo pipefail

INSTALL_CMD="${INSTALL_CMD:-python -m pip install -r requirements.txt}"
VERIFY_CMD="${VERIFY_CMD:-python -m journal.record --check && python -m pytest -q}"
START_CMD="${START_CMD:-python -m journal.record --help}"

case "${1:-help}" in
  install) eval "$INSTALL_CMD" ;;
  verify)  eval "$VERIFY_CMD" ;;
  start)   eval "$START_CMD" ;;
  all)     eval "$INSTALL_CMD" && eval "$VERIFY_CMD" && eval "$START_CMD" ;;
  *) echo "usage: ./init.sh [install|verify|start|all]" ;;
esac
