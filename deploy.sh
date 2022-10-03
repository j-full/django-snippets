#!/usr/bin/bash
# Handles needed things to update and restart
# If you need to activate a virtual env - alternative is if using pipenv, just put pipenv in front of the python3 on line 12
source /bin/activate 

python3 manage.py collectstatic --noinput

sudo systemctl restart gunicorn
