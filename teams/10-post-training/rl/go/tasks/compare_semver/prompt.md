# CompareVersions

Write `func CompareVersions(a, b string) (int, error)` that compares two versions and returns `-1` if `a` is lower, `0` if they are equal and `1` if `a` is higher.

A version is `MAJOR.MINOR.PATCH` with an optional pre-release after a `-`, such as `1.2.3` or `1.0.0-rc.1`.

- MAJOR, MINOR and PATCH are whole numbers without leading zeros (`0` is fine, `01` is not).
- A pre-release is one or more identifiers separated by `.`. An identifier uses only ASCII letters, digits and `-`, and is not empty. A number-only identifier must not have a leading zero (`rc.01` is invalid).
- No build metadata (`+...`), no `v` prefix, no spaces: these are invalid.

Order:

1. Compare MAJOR, then MINOR, then PATCH, as numbers (`1.10.0` is higher than `1.9.0`).
2. If those are equal, a version **with** a pre-release is lower than one without (`1.0.0-rc.1` < `1.0.0`).
3. Two pre-releases are compared identifier by identifier, left to right. Number-only identifiers compare as numbers, and are lower than identifiers with letters. Letter identifiers compare in byte order. If all shared identifiers are equal, the one with fewer identifiers is lower.

If either version is invalid, return 0 and a non-nil error.

Examples:

- `CompareVersions("1.2.3", "1.10.0")` returns `-1, nil`
- `CompareVersions("1.0.0-alpha", "1.0.0-alpha.1")` returns `-1, nil`
- `CompareVersions("1.0", "1.0.0")` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
