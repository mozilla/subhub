workspace(name = "subhub")

load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository", "new_git_repository")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

########################################################################
# Bazel Rules Commits
########################################################################
RULES_PYTHON_COMMIT         = "94677401bc56ed5d756f50b441a6a5c7f735a6d4"
RULES_DOCKER_COMMIT         = "b97ba729728a37e86baefaf66691f733b4bdee19"

########################################################################
# Dependencies
########################################################################

git_repository(
    name = "rules_python",
    remote = "https://github.com/bazelbuild/rules_python.git",
    commit = RULES_PYTHON_COMMIT,
)

git_repository(
    name = "io_bazel_rules_docker",
    remote = "https://github.com/bazelbuild/rules_docker.git",
    commit = RULES_DOCKER_COMMIT,
)

load("@rules_python//python:pip.bzl", "pip_repositories", "pip3_import")
load("@io_bazel_rules_docker//toolchains/docker:toolchain.bzl",
    docker_toolchain_configure="toolchain_configure"
)

docker_toolchain_configure(
  name = "docker_config",
)

load(
    "@io_bazel_rules_docker//repositories:repositories.bzl",
    container_repositories = "repositories",
)
container_repositories()

load(
    "@io_bazel_rules_docker//python3:image.bzl",
    _py3_image_repos = "repositories",
)

_py3_image_repos()

pip_repositories()

pip3_import(
   name = "subhub_dependencies",
   requirements = "//src:requirements.txt",
)


load("@subhub_dependencies//:requirements.bzl", "pip_install")

pip_install()
