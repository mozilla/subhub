#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from subhub.main import create_app

def test_subhub():
    '''
    something
    '''
    app = create_app()
    assert isinstance(app, Flask)
