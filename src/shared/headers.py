# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# TODO(high): Write tests to cover this!

# HEADERS_WHITE_LIST is an array collection containing
# request header entities that are acceptable items to
# be logged into the application's produced logs.
HEADERS_WHITE_LIST = ["Content-Length", "Content-Type", "Host", "X-Amzn-Trace-Id"]

# `dump_headers` is a method to dump from headers from the `requests` library's
# headers and compare against a known list of safe headers for utilization in
# items such as logging and metrics.  It is an O(n) algorithm so as the amount
# of provided headers expands, our runtime thusly does but this being said, the
# network packet transmission time would be expected to dominate this cost.
def dump_safe_headers(request_headers):
    safe_headers = {}
    if request_headers is None:
        return safe_headers
    for header_key in request_headers.keys():
        if header_key not in HEADERS_WHITE_LIST:
            continue
        safe_headers[header_key] = request_headers[header_key]
    return safe_headers


def extract_safe(request_headers, key):
    if request_headers is None:
        return ""
    if key in request_headers:
        return request_headers[key]
    return ""
