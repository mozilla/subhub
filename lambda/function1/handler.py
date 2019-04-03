#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json


def function1(event, context):
    body = {
        'message': 'hello from functions1',
        'input': event,
    }

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    return response
