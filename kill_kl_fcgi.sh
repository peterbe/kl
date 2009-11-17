#!/bin/bash
PIDFILE="/tmp/kl.pid"
kill `cat -- $PIDFILE`
rm -f -- $PIDFILE
