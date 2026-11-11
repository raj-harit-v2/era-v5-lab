# ^0.0 constraint matches major versions that is shouldn't (e.g. 1.0.0)

Upstream issue: https://github.com/Masterminds/semver/issues/133 (opened by @ghost on 2019-11-03). Text copied unchanged.

It appears that if the minor and patch versions match the ^0.0 constraint then Check returns true regardless of what the major version is.

```go
package main

import "github.com/Masterminds/semver"

func main() {
	c, _ := semver.NewConstraint( "^0.0")
	v, _ := semver.NewVersion("1.0.0")
	println(c.Check(v))
}
```

prints true but I would expect based on the readme (`^0.0` is equivalent to `>=0.0.0 <0.1.0`) that it should print false
