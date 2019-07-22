#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import re

import purl
import requests
from behave import then, given, when
from jsoncompare import jsoncompare


def _generate_pprint_json(value):
    return json.dumps(value, sort_keys=True, indent=4)


def generate_assert_failure_message(expected_value, actual_value):
    return "\033[91m\n\nExpected:\n{0}\n\nReceived:\n{1}\n\n\033[0m".format(
        _generate_pprint_json(expected_value), _generate_pprint_json(actual_value)
    )


@given('I am using server "{server}"')
def using_server(context, server):
    context.serverUrl = purl.URL(server)


@given('I set "{name}" header to "{value}"')
def step_impl(context, name, value):
    context.headers[name] = value


@then('I set query parameter "{key}" to {value}')
@then('I set query parameter "{key}" to "{value}"')
@given('I set query parameter "{key}" to {value}')
@given('I set query parameter "{key}" to "{value}"')
def step_impl(context, key, value):
    if key in context.query:
        context.query[key].append(value)
    else:
        context.query[key] = [value]


@then("I should be ready to test the API")
def step_impl(context):
    pass


@given('the "{key}" header should be "{value}"')
@then('the "{key}" header should be "{value}"')
def step_impl(context, key, value):
    assert (
        context.response.headers[key] == value
    ), "Expected {0}, Received: {1}.".format(value, context.response.headers[key])


@then('the "{key}" header should match "{regex}"')
def step_impl(context, key, regex):
    assert re.match(
        regex, context.response.headers[key]
    ), "Matching with pattern {0}, Received: {1}.".format(
        regex, context.response.headers[key]
    )


@given('the response status should be "{status}"')
@then('the response status should be "{status}"')
def response_status(context, status):
    assert context.response.status_code == int(
        status
    ), "Expected {0}, Received: {1}".format(status, context.response.status_code)


@given('I send a "{method}" request to "{url_path_segment}"')
@when('I send a "{method}" request to "{url_path_segment}"')
@then('I send a "{method}" request to "{url_path_segment}"')
def get_request(context, method, url_path_segment):
    headers = context.headers.copy()
    url = context.serverUrl.add_path_segment(url_path_segment)
    for key, value in context.query.items():
        url = url.query_param(key, value)
    context.response = requests.request(
        method, url.as_string(), data=context.text, headers=headers
    )


@then("the JSON should be")
def json_should_be(context):
    expected_value = json.loads(context.text)
    actual_value = json.loads(context.response.text)
    assert expected_value == actual_value, generate_assert_failure_message(
        expected_value, actual_value
    )


@then("the JSON, ignoring order, should be")
def json_should_be(context):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    assert sorted(expected_value) == sorted(
        actual_value
    ), generate_assert_failure_message(sorted(expected_value), sorted(actual_value))


@then('the JSON contents at key "{key}" should be the string "{expected_value}"')
def json_should_be(context, key, expected_value):
    actual_value = json.loads(context.response.text).get(key)
    assert expected_value == actual_value, generate_assert_failure_message(
        expected_value, actual_value
    )


@then('the JSON contents at key "{key}" should be the array')
def json_should_be(context, key):
    actual_value = json.loads(context.response.text).get(key)
    expected_value = json.loads(context.text)
    assert sorted(expected_value) == sorted(
        actual_value
    ), generate_assert_failure_message(sorted(expected_value), sorted(actual_value))


@then('the JSON should be, with fields "{fields}" ignored')
def json_should_be(context, fields):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    same, error_message = jsoncompare.are_same(
        expected_value, actual_value, False, fields
    )
    assert same, error_message


@then('the JSON should be, with field "{field}" ignored')
def json_should_be(context, field):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    same, error_message = jsoncompare.are_same(
        expected_value, actual_value, False, [field]
    )
    assert same, error_message


@then('the JSON should be, with field "{field}" ignored and order ignored')
def json_should_be(context, field):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    same, error_message = jsoncompare.are_same(
        expected_value, actual_value, True, [field]
    )
    assert same, error_message


@then("the JSON should contain")
def json_should_be(context):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    same, error_message = jsoncompare.contains(expected_value, actual_value, True, [])
    assert same, error_message


@then("the JSON should not contain")
def json_should_not_be(context):
    actual_value = json.loads(context.response.text)
    expected_value = json.loads(context.text)
    same, error_message = jsoncompare.contains(expected_value, actual_value, True, [])
    assert not same, error_message
