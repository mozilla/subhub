licenses(["notice"])

package(default_visibility = ["//visibility:public"])

load(
    "@rules_python//python:python.bzl",
    "py_library",
    "py_test",
)
load("@subhub_dependencies//:requirements.bzl", "requirement")

filegroup(
    name = "shared-srcs",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "shared-tests-srcs",
    srcs = glob(["tests/unit/*.py"]),
    visibility = ["//visibility:public"],
)

SHARED_DEPENDENCIES = [
    requirement("pynamodb"),
    requirement("boto3"),
    requirement("structlog"),
]

py_library(
    name = "shared",
    srcs = [":shared-srcs"],
    srcs_version = "PY3",
    deps = SHARED_DEPENDENCIES,
    visibility = ["//visibility:public"],
)

py_test(
    name = "shared_tests",
    srcs = [":shared-tests-srcs"],
    data = glob([
        "tests/unit/fixtures/*.json"
        ]),
    deps = [
        ":shared",
        requirement("mockito"),
        requirement("responses"),
        requirement("mock"),
        requirement("stripe"),
        requirement("tenacity")
    ],
    main = "tests/unit/main.py"
)
