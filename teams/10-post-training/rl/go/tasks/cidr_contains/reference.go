package main

import "errors"

func parseOctets(s string) (uint32, error) {
	var v uint32
	parts := 0
	for i := 0; i <= len(s); {
		j := i
		n := 0
		for j < len(s) && s[j] >= '0' && s[j] <= '9' {
			n = n*10 + int(s[j]-'0')
			if n > 255 {
				return 0, errors.New("octet too large")
			}
			j++
		}
		if j == i || (j-i > 1 && s[i] == '0') {
			return 0, errors.New("bad octet")
		}
		v = v<<8 | uint32(n)
		parts++
		if j == len(s) {
			break
		}
		if s[j] != '.' {
			return 0, errors.New("bad character")
		}
		i = j + 1
	}
	if parts != 4 {
		return 0, errors.New("need four octets")
	}
	return v, nil
}

func CIDRContains(cidr, ip string) (bool, error) {
	slash := -1
	for i := 0; i < len(cidr); i++ {
		if cidr[i] == '/' {
			if slash >= 0 {
				return false, errors.New("two slashes")
			}
			slash = i
		}
	}
	if slash < 0 {
		return false, errors.New("no prefix")
	}
	pfx := cidr[slash+1:]
	if pfx == "" || (len(pfx) > 1 && pfx[0] == '0') || len(pfx) > 2 {
		return false, errors.New("bad prefix")
	}
	n := 0
	for i := 0; i < len(pfx); i++ {
		if pfx[i] < '0' || pfx[i] > '9' {
			return false, errors.New("bad prefix")
		}
		n = n*10 + int(pfx[i]-'0')
	}
	if n > 32 {
		return false, errors.New("prefix too long")
	}
	base, err := parseOctets(cidr[:slash])
	if err != nil {
		return false, err
	}
	addr, err := parseOctets(ip)
	if err != nil {
		return false, err
	}
	var mask uint32
	if n > 0 {
		mask = ^uint32(0) << (32 - uint(n))
	}
	return base&mask == addr&mask, nil
}
