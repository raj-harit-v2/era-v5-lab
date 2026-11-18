package main

import "errors"

func isKeyStart(c byte) bool { return c == '_' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' }
func isKeyChar(c byte) bool  { return isKeyStart(c) || c >= '0' && c <= '9' }

func ParseKV(line string) (map[string]string, error) {
	out := map[string]string{}
	i, n := 0, len(line)
	for {
		for i < n && line[i] == ' ' {
			i++
		}
		if i >= n {
			return out, nil
		}
		if !isKeyStart(line[i]) {
			return nil, errors.New("bad key")
		}
		j := i
		for j < n && isKeyChar(line[j]) {
			j++
		}
		if j >= n || line[j] != '=' {
			return nil, errors.New("missing =")
		}
		key := line[i:j]
		i = j + 1
		var val []byte
		if i < n && line[i] == '"' {
			i++
			closed := false
			for i < n {
				c := line[i]
				if c == '\\' {
					if i+1 >= n || (line[i+1] != '"' && line[i+1] != '\\') {
						return nil, errors.New("bad escape")
					}
					val = append(val, line[i+1])
					i += 2
					continue
				}
				if c == '"' {
					closed = true
					i++
					break
				}
				val = append(val, c)
				i++
			}
			if !closed {
				return nil, errors.New("unterminated quote")
			}
			if i < n && line[i] != ' ' {
				return nil, errors.New("text after quote")
			}
		} else {
			for i < n && line[i] != ' ' {
				if line[i] == '"' || line[i] == '=' {
					return nil, errors.New("bad bare value")
				}
				val = append(val, line[i])
				i++
			}
		}
		out[key] = string(val)
	}
}
