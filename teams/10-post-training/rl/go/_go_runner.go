// Runs inside the sandbox (copied there as runner.go next to the candidate's solution.go and a generated entry.go).
//
// It gets inputs only. It never sees an expected value, so nothing it writes can be "made to match": the verifier
// (the parent process) compares the outputs with the expected values, which are never in this process or this folder.
//
// Usage (by go_verifier.py):  ./sol <case_timeout_s>
// Reads  cases.json   (a list of {"args": [...]}, each arg is JSON)
// Writes results.json (a list of {"ok": true, "value": ...} or {"ok": false, "error": "error"|"panic"|...}).
// The file name starts with "_" so that `go build` in the repository ignores it; the verifier copies it as runner.go.
package main

import (
	"encoding/json"
	"os"
	"reflect"
	"strconv"
	"time"
)

type result struct {
	Ok    bool            `json:"ok"`
	Value json.RawMessage `json:"value,omitempty"`
	Error string          `json:"error,omitempty"`
	Mro   []string        `json:"mro,omitempty"`
}

const maxResultBytes = 4_000_000

var errorType = reflect.TypeOf((*error)(nil)).Elem()

func fail(kind string) result { return result{Ok: false, Error: kind, Mro: []string{kind}} }

// call runs the entry point on one case. A returned error is {"ok": false, "error": "error"}.
func call(fn reflect.Value, ft reflect.Type, args []json.RawMessage) result {
	if ft.Kind() != reflect.Func || ft.IsVariadic() || ft.NumIn() != len(args) {
		return fail("signature")
	}
	in := make([]reflect.Value, len(args))
	for i := range args {
		p := reflect.New(ft.In(i))
		if err := json.Unmarshal(args[i], p.Interface()); err != nil {
			return fail("argument")
		}
		in[i] = p.Elem()
	}
	out := fn.Call(in)
	n := len(out)
	if n < 1 || n > 2 {
		return fail("signature")
	}
	last := out[n-1]
	if ft.Out(n-1) == errorType {
		if !last.IsNil() {
			return fail("error")
		}
		if n == 1 { // func(...) error that returned nil
			return result{Ok: true, Value: json.RawMessage("null")}
		}
	} else if n == 2 {
		return fail("signature")
	}
	b, err := json.Marshal(out[0].Interface()) // NaN, Inf and unsupported types fail here
	if err != nil {
		return fail("marshal")
	}
	return result{Ok: true, Value: b}
}

func runCase(fn reflect.Value, ft reflect.Type, args []json.RawMessage, limit time.Duration) (result, bool) {
	done := make(chan result, 1)
	go func() {
		defer func() {
			if r := recover(); r != nil {
				done <- fail("panic")
			}
		}()
		done <- call(fn, ft, args)
	}()
	select {
	case r := <-done:
		return r, false
	case <-time.After(limit):
		return fail("Timeout"), true
	}
}

func write(results []result) {
	payload, err := json.Marshal(results)
	if err != nil || len(payload) > maxResultBytes {
		bad := make([]result, len(results))
		for i := range bad {
			bad[i] = fail("ResultTooLarge")
		}
		payload, _ = json.Marshal(bad)
	}
	_ = os.WriteFile("results.json", payload, 0o644)
}

func main() {
	limit := 2 * time.Second
	if len(os.Args) > 1 {
		if s, err := strconv.ParseFloat(os.Args[1], 64); err == nil && s > 0 {
			limit = time.Duration(s * float64(time.Second))
		}
	}
	raw, err := os.ReadFile("cases.json")
	if err != nil {
		os.Exit(2)
	}
	var cases []struct {
		Args []json.RawMessage `json:"args"`
	}
	if json.Unmarshal(raw, &cases) != nil {
		os.Exit(2)
	}
	fn := reflect.ValueOf(Entry)
	ft := fn.Type()
	results := make([]result, 0, len(cases))
	for _, c := range cases {
		r, timedOut := runCase(fn, ft, c.Args, limit)
		results = append(results, r)
		if timedOut { // the stuck goroutine cannot be stopped: every other case fails too, and the run ends here
			for len(results) < len(cases) {
				results = append(results, fail("Timeout"))
			}
			break
		}
	}
	write(results)
	os.Exit(0) // do not wait for goroutines that the candidate started
}
