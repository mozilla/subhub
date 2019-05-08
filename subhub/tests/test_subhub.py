#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import connexion
from subhub.app import create_app


def test_subhub():
    """
    something
    """
    app = create_app()
    assert isinstance(app, connexion.FlaskApp)
