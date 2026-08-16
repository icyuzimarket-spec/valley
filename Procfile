release: python manage.py migrate --noinput
web: gunicorn valley_investment.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 60 --access-logfile - --error-logfile -
