#!/bin/sh

set -e  # Exit on any error

echo ""
echo "------------------------------------------"
echo "🚀 Starting container with ROLE=\"$ROLE\""
echo "------------------------------------------"

case "$ROLE" in
  flask)
    echo "🟢 Starting Flask API (Server)..."
    . ~/backend/venv/bin/activate
    exec gunicorn -w 4 -b 0.0.0.0:port run.wsgi:application
    ;;
    
  celery)
    echo "🔧 Starting Slack Celery worker with tasks concurrently : $CELERY_WORKER"
    . ~/backend/venv/bin/activate
    #exec celery -A celery_app.init worker -c $CELERY_WORKER --loglevel=info -Q $CELERY_QUEUES -n data_sources
    echo "this is a place holder for the celery"
    exit 0
    ;;

  *)
    echo "❌ ERROR: Unknown ROLE \"$ROLE\""
    echo "Valid roles are: flask, celery"
    exit 1
    ;;
esac
