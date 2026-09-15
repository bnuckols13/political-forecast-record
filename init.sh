#!/usr/bin/env bash
# Standard startup path for this project. The next session reaches a working
# state by reading PROGRESS.md and running this script. If it can't, the last
# session didn't finish.
#
# This project uses a venv, which is a deliberate deviation from crypto-trading's
# no-venv convention. Reason: requirements.txt pins pandas>=3.0, and pandas 3.0 is
# a breaking change (Copy-on-Write mandatory, chained assignment gone). The system
# interpreter carries pandas 2.3.3 and crypto-trading runs against pandas 2.x, so a
# system-wide install here would silently break that project's backtests.
#
# The daily record path (journal/record.py, venues/manifold.py) is stdlib-only and
# runs under the system interpreter too. The venv is for the analysis layer.
set -euo pipefail

PY="${PY:-./.venv/Scripts/python.exe}"
[ -x "$PY" ] || PY="./.venv/bin/python"          # POSIX venv layout
[ -x "$PY" ] || PY="python"                      # no venv yet; install creates it

INSTALL_CMD="${INSTALL_CMD:-python -m venv .venv && $PY -m pip install -r requirements.txt}"
VERIFY_CMD="${VERIFY_CMD:-$PY -m journal.record --check && $PY -m pytest -q}"
START_CMD="${START_CMD:-$PY -m journal.record --help}"

case "${1:-help}" in
  install) eval "$INSTALL_CMD" ;;
  verify)  eval "$VERIFY_CMD" ;;
  start)   eval "$START_CMD" ;;
  all)     eval "$INSTALL_CMD" && eval "$VERIFY_CMD" && eval "$START_CMD" ;;
  *) echo "usage: ./init.sh [install|verify|start|all]" ;;
esac
