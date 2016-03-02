#!/bin/bash

virtualenv -p /usr/bin/python2.7 venv
. venv/bin/activate
pip install -r requirements.txt

python backup.py
