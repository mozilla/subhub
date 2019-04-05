#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json


def handle(event, context):

    try:
        from subhub.app import app
        result = str(app)
    except Exception as ex:
        result = str(ex)
    body = {
        'message': 'hello from function1',
        'result': result,
    }

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    return response
