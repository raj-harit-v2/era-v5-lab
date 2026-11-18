# CIDRContains

Write `func CIDRContains(cidr, ip string) (bool, error)` that says whether an IPv4 address is inside a CIDR block such as `10.0.0.0/8`.

- Both texts must be strict. An address is four decimal numbers from 0 to 255 separated by `.`. No leading zeros (`01` is invalid, `0` is fine), no signs, no spaces, no other characters.
- A block is an address, then `/`, then a prefix length from 0 to 32 written in decimal without leading zeros (`/08` is invalid).
- The address in the block may have host bits set. `10.1.2.3/8` is the same block as `10.0.0.0/8`.
- A prefix of 0 contains every address. A prefix of 32 contains only that address.
- Do not use the `net` or `net/netip` packages.
- If either text is invalid, return `false` and a non-nil error.

Examples:

- `CIDRContains("192.168.0.0/16", "192.168.44.7")` returns `true, nil`
- `CIDRContains("10.0.0.0/8", "11.0.0.1")` returns `false, nil`
- `CIDRContains("10.0.0.0/33", "10.0.0.1")` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
