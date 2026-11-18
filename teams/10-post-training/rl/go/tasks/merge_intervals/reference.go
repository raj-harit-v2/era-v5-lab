package main

import (
	"errors"
	"sort"
)

func MergeIntervals(iv [][]int) ([][]int, error) {
	cp := make([][]int, 0, len(iv))
	for _, p := range iv {
		if len(p) != 2 || p[0] > p[1] {
			return nil, errors.New("bad interval")
		}
		cp = append(cp, []int{p[0], p[1]})
	}
	sort.Slice(cp, func(i, j int) bool { return cp[i][0] < cp[j][0] })
	out := [][]int{}
	for _, p := range cp {
		if n := len(out); n > 0 && p[0] <= out[n-1][1]+1 {
			if p[1] > out[n-1][1] {
				out[n-1][1] = p[1]
			}
		} else {
			out = append(out, p)
		}
	}
	return out, nil
}
