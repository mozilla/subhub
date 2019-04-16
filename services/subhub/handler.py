#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from subhub.app import create_app

def handle(event, context):
    try:
        app = create_app()
        result = 'good to go!'
    except Exception as ex:
        result = str(ex)

    body = {
        "message": "well hello there buddy!",
        "result": result,
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
