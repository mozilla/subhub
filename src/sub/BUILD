licenses(["notice"])

package(default_visibility = ["//visibility:public"])

load(
    "@rules_python//python:python.bzl",
    "py_binary",
    "py_test",
)
load("@subhub_dependencies//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")

SUB_DEPENDENCIES = [
        requirement("newrelic"),
        requirement("connexion"),
        requirement("jsonschema"),
        requirement("inflection"),
        requirement("openapi_spec_validator"),
        requirement("stripe"),
        requirement("flask_cors"),
        requirement("cachetools"),
        requirement("python-json-logger"),
        requirement("pyinstrument"),
        requirement("tenacity"),
        "//src/shared:shared",
]

py_binary(
    name = "sub",
    python_version = "PY3",
    srcs = glob(["*.py"]),
    deps = SUB_DEPENDENCIES,
    data = [
        "swagger.yaml",
    ],
    main = "app.py",
    imports = ["//src/sub"],
    visibility = ["//visibility:public"],
)

py3_image(
    name = "sub_docker",
    srcs = glob(["*.py"]),
    deps = SUB_DEPENDENCIES,
    main = "app.py",
)

py_test(
    name = "sub_tests",
    srcs = glob([
        "tests/*.py",
        "tests/unit/*.py",
        "tests/unit/customer/*.py"
        ]),
    data = glob([
        "tests/unit/customer/*.json",
        "tests/unit/fixtures/*.json"
        ]),
    deps = [
        ":sub",
        requirement("psutil"),
    ],
    main = "tests/main.py"
)
