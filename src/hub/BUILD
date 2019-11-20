licenses(["notice"])

package(default_visibility = ["//visibility:public"])

load(
    "@rules_python//python:python.bzl",
    "py_binary",
    "py_test",
)
load("@subhub_dependencies//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")

HUB_DEPENDENCIES = [
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
        requirement("attrdict"),
        "//src/shared:shared",
]

filegroup(
    name = "hub-routes-srcs",
    srcs = glob(["routes/*.py"]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "hub-vendor-srcs",
    srcs = glob(["vendor/*.py"]),
    visibility = ["//visibility:public"],
)

py_binary(
    name = "hub",
    python_version = "PY3",
    srcs = [
        ":hub-routes-srcs",
        ":hub-vendor-srcs",
        "app.py"
    ],
    deps = HUB_DEPENDENCIES,
    data = [
        "swagger.yaml",
    ],
    main = "app.py",
    visibility = ["//visibility:public"],
)

py3_image(
    name = "hub_docker",
    srcs = glob(["*.py"]),
    deps = HUB_DEPENDENCIES,
    main = "app.py",
)

py_test(
    name = "hub_tests",
    srcs = glob([
        "tests/main.py",
        "tests/unit/*.py",
        "tests/unit/stripe/customer/*.py",
        "tests/unit/stripe/event/*.py",
        "tests/unit/stripe/event/*.py",
        "tests/unit/stripe/payment/*.py",
        "tests/conftest.py"
        ]),
    data = glob([
        "tests/unit/customer/*.json",
        "tests/unit/fixtures/*.json",
        "tests/unit/stripe/charge/*.json",
        "tests/unit/stripe/event/*.json",
        "tests/unit/stripe/invoice/*.json",
        "tests/unit/stripe/event/*.json",
        ]),
    deps = [
        ":hub",
        requirement("psutil"),
        requirement("mockito"),
    ],
    main = "tests/main.py"
)
