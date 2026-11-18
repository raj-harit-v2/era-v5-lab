package main

import "errors"

func SplitBalanced(xs []int, parts int) ([][]int, error) {
	if parts <= 0 {
		return nil, errors.New("parts must be positive")
	}
	out := make([][]int, 0, parts)
	base, extra := len(xs)/parts, len(xs)%parts
	pos := 0
	for i := 0; i < parts; i++ {
		size := base
		if i < extra {
			size++
		}
		chunk := make([]int, size)
		copy(chunk, xs[pos:pos+size])
		out = append(out, chunk)
		pos += size
	}
	return out, nil
}
