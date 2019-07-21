import json


def _generate_pprint_json(value):
    return json.dumps(value, sort_keys=True, indent=4)


def generate_assert_failure_message(expected_value, actual_value):
    return "\033[91m\n\nExpected:\n{0}\n\nReceived:\n{1}\n\n\033[0m".format(
        _generate_pprint_json(expected_value), _generate_pprint_json(actual_value)
    )
