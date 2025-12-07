#!/bin/sh

set -e  # Exit on any error

echo ""
echo "------------------------------------------"
echo "🚀 Starting container with ROLE=\"$ROLE\""
echo "------------------------------------------"

case "$ROLE" in
  flask)
    echo "🟢 Starting Flask API (Server)..."
    exec venv/bin/python3.11 app.py
    ;;
    
  celery)
    echo "🔧 Starting Celery worker with $CELERY_WORKER concurrent workers"
    # Using prefork pool for parallel processing (document conversion is now remote HTTP)
    exec venv/bin/celery -A celery_app.init worker -c $CELERY_WORKER --pool=prefork --loglevel=info -Q $CELERY_QUEUES -n data_sources
    ;;

  debug)
    echo "🐞 Debug mode activated — container will stay alive."
    tail -f /dev/null
    ;;

  *)
    echo "❌ ERROR: Unknown ROLE \"$ROLE\""
    echo "Valid roles are: flask, celery, debug"
    exit 1
    ;;
esac
