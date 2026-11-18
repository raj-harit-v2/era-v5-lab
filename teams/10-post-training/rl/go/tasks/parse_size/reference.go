package main

import (
	"errors"
	"math/big"
	"strings"
)

var sizeUnits = map[string]int64{
	"": 1, "b": 1,
	"kb": 1000, "mb": 1000000, "gb": 1000000000,
	"kib": 1 << 10, "mib": 1 << 20, "gib": 1 << 30,
}

func ParseSize(s string) (int64, error) {
	s = strings.TrimSpace(s)
	i, dots := 0, 0
	for i < len(s) && (s[i] >= '0' && s[i] <= '9' || s[i] == '.') {
		if s[i] == '.' {
			dots++
		}
		i++
	}
	num := s[:i]
	if dots > 1 || strings.Trim(num, ".") == "" {
		return 0, errors.New("bad number")
	}
	mult, ok := sizeUnits[strings.ToLower(strings.TrimSpace(s[i:]))]
	if !ok {
		return 0, errors.New("bad unit")
	}
	r, ok := new(big.Rat).SetString(num)
	if !ok {
		return 0, errors.New("bad number")
	}
	r.Mul(r, new(big.Rat).SetInt64(mult))
	q := new(big.Int).Quo(r.Num(), r.Denom()) // non-negative, so Quo rounds down
	if !q.IsInt64() {
		return 0, errors.New("too large")
	}
	return q.Int64(), nil
}
