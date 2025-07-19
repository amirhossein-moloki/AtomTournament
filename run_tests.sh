#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python manage.py test
