#!/bin/bash

# THIS IS FOR TESTING TO RUN THIS DJANGO WITH NGINX LOCALLY

# TO KILL THE FCGI THREAD KILL $PIDFILE




# Replace these three settings.
PROJDIR="/home/peterbe/kl"
PIDFILE="/tmp/kl.pid"
SOCKET="/tmp/kl.sock"

OUTLOG="/tmp/kl.out.log"
ERRLOG="/tmp/kl.err.log"


cd $PROJDIR
if [ -f $PIDFILE ]; then
    kill `cat -- $PIDFILE`
    rm -f -- $PIDFILE
fi

#exec /usr/bin/env - \
#  PYTHONPATH="../python:.." \
#  ./manage.py runfcgi method=threaded pidfile=$PIDFILE host=127.0.0.1 port=9000 outlog=$OUTLOG errlog=$ERRLOG

python \
   ./manage.py runfcgi method=threaded pidfile=$PIDFILE host=127.0.0.1 port=9000 outlog=$OUTLOG errlog=$ERRLOG \
       --settings=fcgi_settings
