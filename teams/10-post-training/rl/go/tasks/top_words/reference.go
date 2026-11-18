package main

import (
	"sort"
	"strings"
)

func isLetter(b byte) bool { return (b >= 'a' && b <= 'z') || (b >= 'A' && b <= 'Z') }

func TopWords(text string, k int) []string {
	counts := map[string]int{}
	n := len(text)
	for i := 0; i < n; {
		if !isLetter(text[i]) {
			i++
			continue
		}
		j := i
		for j < n {
			if isLetter(text[j]) {
				j++
			} else if text[j] == '\'' && j+1 < n && isLetter(text[j+1]) {
				j++
			} else {
				break
			}
		}
		counts[strings.ToLower(text[i:j])]++
		i = j
	}
	words := make([]string, 0, len(counts))
	for w := range counts {
		words = append(words, w)
	}
	sort.Slice(words, func(a, b int) bool {
		if counts[words[a]] != counts[words[b]] {
			return counts[words[a]] > counts[words[b]]
		}
		return words[a] < words[b]
	})
	if k < 0 {
		k = 0
	}
	if len(words) > k {
		words = words[:k]
	}
	return words
}
