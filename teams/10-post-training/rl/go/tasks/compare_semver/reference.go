package main

import (
	"errors"
	"strconv"
	"strings"
)

type ver struct {
	nums [3]int
	pre  []string
}

func isNum(s string) bool {
	if s == "" {
		return false
	}
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	return true
}

func parse(v string) (ver, error) {
	var r ver
	core := v
	if i := strings.IndexByte(v, '-'); i >= 0 {
		core = v[:i]
		pre := v[i+1:]
		r.pre = strings.Split(pre, ".")
		for _, id := range r.pre {
			if id == "" {
				return r, errors.New("empty identifier")
			}
			for k := 0; k < len(id); k++ {
				c := id[k]
				if !(c == '-' || (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
					return r, errors.New("bad identifier")
				}
			}
			if isNum(id) && len(id) > 1 && id[0] == '0' {
				return r, errors.New("leading zero")
			}
		}
	}
	parts := strings.Split(core, ".")
	if len(parts) != 3 {
		return r, errors.New("need three numbers")
	}
	for i, p := range parts {
		if !isNum(p) || (len(p) > 1 && p[0] == '0') {
			return r, errors.New("bad number")
		}
		n, err := strconv.Atoi(p)
		if err != nil {
			return r, err
		}
		r.nums[i] = n
	}
	return r, nil
}

func cmpInt(a, b int) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}

func CompareVersions(a, b string) (int, error) {
	x, err := parse(a)
	if err != nil {
		return 0, err
	}
	y, err := parse(b)
	if err != nil {
		return 0, err
	}
	for i := 0; i < 3; i++ {
		if c := cmpInt(x.nums[i], y.nums[i]); c != 0 {
			return c, nil
		}
	}
	if x.pre == nil && y.pre == nil {
		return 0, nil
	}
	if x.pre == nil {
		return 1, nil
	}
	if y.pre == nil {
		return -1, nil
	}
	for i := 0; i < len(x.pre) && i < len(y.pre); i++ {
		p, q := x.pre[i], y.pre[i]
		if p == q {
			continue
		}
		pn, qn := isNum(p), isNum(q)
		switch {
		case pn && qn:
			pi, _ := strconv.Atoi(p)
			qi, _ := strconv.Atoi(q)
			return cmpInt(pi, qi), nil
		case pn:
			return -1, nil
		case qn:
			return 1, nil
		default:
			return strings.Compare(p, q), nil
		}
	}
	return cmpInt(len(x.pre), len(y.pre)), nil
}
