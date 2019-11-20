# Bazel

## Commands

### Sub Component Dependencies

```
bazel query 'deps(//src/sub)'
```

### Shared Component Dependencies

```
bazel query 'deps(//src/shared)'
```

### Running the Sub Component

```
DEPLOYED_ENV=local BRANCH=master bazel run //src/sub
```

### Running the Hub Component

```
DEPLOYED_ENV=local BRANCH=master bazel run //src/hub
```
