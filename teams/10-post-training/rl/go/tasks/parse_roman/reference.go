package main

import "errors"

var pairs = []struct {
	v int
	r string
}{{1000, "M"}, {900, "CM"}, {500, "D"}, {400, "CD"}, {100, "C"}, {90, "XC"}, {50, "L"}, {40, "XL"}, {10, "X"}, {9, "IX"}, {5, "V"}, {4, "IV"}, {1, "I"}}

func ParseRoman(s string) (int, error) {
	n, rest := 0, s
	for _, p := range pairs {
		for len(rest) >= len(p.r) && rest[:len(p.r)] == p.r {
			n += p.v
			rest = rest[len(p.r):]
		}
	}
	if s == "" || rest != "" || n > 3999 {
		return 0, errors.New("invalid roman numeral")
	}
	// accept only the canonical form
	if toRoman(n) != s {
		return 0, errors.New("not canonical")
	}
	return n, nil
}

func toRoman(n int) string {
	out := ""
	for _, p := range pairs {
		for n >= p.v {
			out += p.r
			n -= p.v
		}
	}
	return out
}
