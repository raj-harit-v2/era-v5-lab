package main

import (
	"errors"
	"math"
)

func ExpandRLE(s string, maxLen int) (string, error) {
	var out []byte
	total := 0
	for i := 0; i < len(s); {
		j := i
		n := 0
		for j < len(s) && s[j] >= '0' && s[j] <= '9' {
			if j == i && s[j] == '0' {
				return "", errors.New("count starts with zero")
			}
			if n > (math.MaxInt-9)/10 {
				return "", errors.New("count too large")
			}
			n = n*10 + int(s[j]-'0')
			j++
		}
		if j == i || j >= len(s) || n < 1 {
			return "", errors.New("bad group")
		}
		if n > maxLen-total {
			return "", errors.New("result too long")
		}
		total += n
		for k := 0; k < n; k++ {
			out = append(out, s[j])
		}
		i = j + 1
	}
	return string(out), nil
}
