#!/usr/bin/env bash

sudo usermod -a -G docker $USER
cd /opt/subhub
pip3 install -r automation_requirements.txt
python3 dodo.py
