package stats

import "testing"

func TestSum(t *testing.T) {
	cases := []struct {
		name string
		in   []int
		want int
	}{
		{"empty", nil, 0},
		{"one", []int{7}, 7},
		{"many", []int{1, 2, 3}, 6},
	}
	for _, c := range cases {
		if got := Sum(c.in); got != c.want {
			t.Errorf("%s: Sum(%v) = %d, want %d", c.name, c.in, got, c.want)
		}
	}
}
