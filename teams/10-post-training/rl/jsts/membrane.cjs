'use strict';
// Loads the candidate module in its own V8 context (no require, no process, no fs, no jest globals) and hands the
// spec only copies: primitives, arrays, plain objects, Map, Set, Date are deep-copied into the test realm; functions
// and class instances are wrapped. No test-realm object is ever passed into the candidate context.
const vm = require('vm');
const fs = require('fs');
function load(file) {
  const ctx = vm.createContext(Object.create(null), { codeGeneration: { strings: false, wasm: false } });
  const C = vm.runInContext(`({ ObjectProto: Object.prototype, ArrayProto: Array.prototype, MapProto: Map.prototype,
    SetProto: Set.prototype, DateProto: Date.prototype, ErrorProto: Error.prototype, isArray: Array.isArray,
    newObj: () => ({}), newArr: () => [], newMap: () => new Map(), newSet: () => new Set(), newDate: (t) => new Date(t),
    mapSet: Map.prototype.set, setAdd: Set.prototype.add, getTime: Date.prototype.getTime,
    mapEntries: (m) => Array.from(m.entries()), setValues: (s) => Array.from(s.values()) })`, ctx);
  vm.runInContext(`globalThis.console = { log() {}, error() {}, warn() {}, info() {}, debug() {} };
    globalThis.module = { exports: {} }; globalThis.exports = globalThis.module.exports;`, ctx);
  const getProto = Object.getPrototypeOf;
  const targets = new WeakMap();   // test-realm proxy -> candidate object
  const ctors = new Map();         // candidate constructor -> test-realm wrapper
  function toCand(v) {
    if (v === null || (typeof v !== 'object' && typeof v !== 'function')) return v;
    if (targets.has(v)) return targets.get(v);
    if (Array.isArray(v)) { const a = C.newArr(); v.forEach((x, i) => { a[i] = toCand(x); }); return a; }
    if (v instanceof Map) { const m = C.newMap(); for (const [k, x] of v) Reflect.apply(C.mapSet, m, [toCand(k), toCand(x)]); return m; }
    if (v instanceof Set) { const s = C.newSet(); for (const x of v) Reflect.apply(C.setAdd, s, [toCand(x)]); return s; }
    if (v instanceof Date) return C.newDate(v.getTime());
    const p = getProto(v);
    if (p === Object.prototype || p === null) { const o = C.newObj(); for (const k of Object.keys(v)) o[k] = toCand(v[k]); return o; }
    throw new TypeError('membrane: unsupported argument type');
  }
  function toTest(v) {
    if (v === null || (typeof v !== 'object' && typeof v !== 'function')) return v;
    if (typeof v === 'function') return wrapFn(v);
    if (C.isArray(v)) { const n = Reflect.get(v, 'length'); const a = []; for (let i = 0; i < n; i++) a.push(toTest(Reflect.get(v, i))); return a; }
    const p = getProto(v);
    if (p === C.MapProto) return new Map(C.mapEntries(v).map(([k, x]) => [toTest(k), toTest(x)]));
    if (p === C.SetProto) return new Set(C.setValues(v).map(toTest));
    if (p === C.DateProto) return new Date(Reflect.apply(C.getTime, v, []));
    if (p === C.ObjectProto || p === null) { const o = {}; for (const k of Object.keys(v)) o[k] = toTest(Reflect.get(v, k)); return o; }
    return instanceProxy(v);
  }
  function wrapperFor(obj) {   // the closest exported class in the prototype chain
    for (let p = getProto(obj); p; p = getProto(p)) for (const [c, w] of ctors) if (c.prototype === p) return w;
    return null;
  }
  function instanceProxy(cand) {
    const w = wrapperFor(cand);
    const dummy = Object.create(w ? w.prototype : Object.prototype);
    const px = new Proxy(dummy, {
      get(_, k) { let v; try { v = Reflect.get(cand, k, cand); } catch (e) { throw errToTest(e); } return typeof v === 'function' ? wrapFn(v, cand) : toTest(v); },
      set(_, k, v) { try { return Reflect.set(cand, k, toCand(v), cand); } catch (e) { throw errToTest(e); } },
      has(_, k) { return Reflect.has(cand, k); },
      ownKeys() { return Reflect.ownKeys(cand).filter((k) => typeof k === 'string'); },
      getOwnPropertyDescriptor(_, k) {
        const d = Reflect.getOwnPropertyDescriptor(cand, k);
        return d && { configurable: true, enumerable: !!d.enumerable, writable: true, value: toTest(Reflect.get(cand, k, cand)) };
      },
    });
    targets.set(px, cand);
    return px;
  }
  function errToTest(e) {
    if (e === null || typeof e !== 'object') return new Error(String(e));
    const m = Reflect.get(e, 'message');
    const err = new Error(typeof m === 'string' ? m : '');
    const w = wrapperFor(e);
    if (w) Object.setPrototypeOf(err, w.prototype);
    return err;
  }
  function wrapFn(f, self) {
    if (self === undefined && ctors.has(f)) return ctors.get(f);
    const w = function (...args) {
      const a = args.map(toCand);
      let r;
      try { r = new.target ? Reflect.construct(f, a) : Reflect.apply(f, self !== undefined ? self : (targets.get(this)), a); }
      catch (e) { throw errToTest(e); }
      return toTest(r);
    };
    if (self === undefined) {
      const isErr = (() => { for (let p = f.prototype; p; p = getProto(p)) if (p === C.ErrorProto) return true; return false; })();
      w.prototype = Object.create(isErr ? Error.prototype : Object.prototype);
      ctors.set(f, w);
    }
    return w;
  }
  vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: 'candidate.js', timeout: 10000 });
  const raw = vm.runInContext('module.exports', ctx);
  const out = {};
  for (const k of Object.keys(raw)) { const v = Reflect.get(raw, k); if (typeof v === 'function') wrapFn(v); }
  for (const k of Object.keys(raw)) out[k] = toTest(Reflect.get(raw, k));
  return out;
}
module.exports = { load };
