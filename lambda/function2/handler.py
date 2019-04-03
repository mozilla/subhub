#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json


def handle(event, context):
    body = {
        'message': 'hello from function2',
        'input': event,
    }

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    return response
