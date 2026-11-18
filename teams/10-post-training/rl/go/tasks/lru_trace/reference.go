package main

import (
	"container/list"
	"errors"
	"strings"
)

type entry struct{ key, val string }

func LRUTrace(capacity int, ops []string) ([]string, error) {
	if capacity <= 0 {
		return nil, errors.New("capacity must be positive")
	}
	ll := list.New()
	idx := map[string]*list.Element{}
	out := []string{}
	for _, op := range ops {
		f := strings.Split(op, " ")
		switch {
		case len(f) == 3 && f[0] == "put" && f[1] != "" && f[2] != "":
			if e, ok := idx[f[1]]; ok {
				e.Value.(*entry).val = f[2]
				ll.MoveToFront(e)
			} else {
				idx[f[1]] = ll.PushFront(&entry{f[1], f[2]})
				if ll.Len() > capacity {
					last := ll.Back()
					delete(idx, last.Value.(*entry).key)
					ll.Remove(last)
				}
			}
		case len(f) == 2 && f[0] == "get" && f[1] != "":
			if e, ok := idx[f[1]]; ok {
				ll.MoveToFront(e)
				out = append(out, e.Value.(*entry).val)
			} else {
				out = append(out, "-")
			}
		default:
			return nil, errors.New("bad operation")
		}
	}
	return out, nil
}
