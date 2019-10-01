# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import requests
import responses

from shared.headers import dump_safe_headers


def test_no_headers_provided():
    headers = dump_safe_headers(None)
    assert len(headers) == 0


@responses.activate
def test_non_safe_headers_no_provided():
    def request_callback(request):
        payload = json.loads(request.body)
        resp_body = {"value": sum(payload["numbers"])}
        headers = {
            "Authorization": "728d329e-0e86-11e4-a748-0c84dc037c13",
            "Host": "127.0.0.1",
        }
        return (200, headers, json.dumps(resp_body))

    responses.add_callback(
        responses.POST,
        "http://dev.fxa.mozilla-subhub.app/plans",
        callback=request_callback,
        content_type="application/json",
    )

    resp = requests.post(
        "http://dev.fxa.mozilla-subhub.app/plans",
        json.dumps({"numbers": [1, 2, 3]}),
        headers={"content-type": "application/json"},
    )

    headers = dump_safe_headers(resp.headers)
    assert len(headers) == 2
    assert responses.calls[0].response.headers["Host"] == "127.0.0.1"
    assert responses.calls[0].response.headers["Content-Type"] == "application/json"
