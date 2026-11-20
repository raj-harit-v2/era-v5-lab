'use strict';
// Runs inside the sandbox (copied there as runner.js by js_verifier.py).
//
// SECURITY MODEL
// --------------
// Workers are spawned with eval:true using the WORKER_BOOT string constant, which is
// embedded in this file and never written to the work directory.  Candidate code cannot
// replace the bootstrap by overwriting /work/runner.js.
//
// Inside each Worker, parentPort and workerData are nulled before candidate code runs.
// This neutralises the process.getBuiltinModule('worker_threads').parentPort attack path
// (Node.js 22.3+): both require('worker_threads') and process.getBuiltinModule(...)
// return the same cached module object, so a single assignment poisons both routes.
//
// A per-invocation nonce is included in every authentic result message and checked by
// the main thread.  A message without the correct nonce is rejected as malformed.
//
// Function.prototype.call/apply, Promise.prototype.then, and
// MessagePort.prototype.postMessage are captured as bound functions before
// new Function(code)(...) runs.  Bound functions store a direct reference to the original
// in [[BoundTargetFunction]] and invoke it via [[BoundCall]] — no prototype chain lookup —
// so candidate code that mutates these prototype properties after captures are taken cannot
// intercept bootstrap operations.  TypeError/RangeError/SyntaxError prototypes are captured
// as plain references (var _TypeErrorProto = TypeError.prototype, etc.); they are not bound
// functions.  Object.assign is not captured; result objects use null-prototype object
// literals ({ __proto__: null, ... }) so Object.assign replacement has no effect on
// result message construction.
//
// Exception classification uses util.types.isNativeError (V8 IsNativeError()) and captured
// prototype identities (isPrototypeOf with subclass semantics).  isNativeError accepts
// genuine native Errors — including instances of user-defined subclasses such as
// class CustomTypeError extends TypeError {} — and rejects plain objects whose prototypes
// were set to Error-like values via Object.setPrototypeOf.  The prototype-identity checks
// are subclass-aware: CustomTypeError instances satisfy isPrototypeOf(TypeError.prototype)
// and are classified as TypeError.  globalThis.TypeError replacement and constructor.name
// forgery have no effect because prototype references are captured before candidate code.
// SAME-REALM LIMITATION: Object.setPrototypeOf(realNativeError, TypeError.prototype) where
// realNativeError is an existing native Error passes isNativeError AND the prototype-identity
// check and is classified as TypeError; cannot be resolved in a shared JS realm.
//
// Returning undefined, NaN, or Infinity is reported as 'InvalidReturn', not 'TypeError'.
// This prevents a function that returns undefined for non-string inputs from accidentally
// satisfying a {"raises": "TypeError"} test case.
//
// Usage (by js_verifier.py):  node runner.js <workdir> <entryPoint> <caseTimeoutS>

const { Worker, isMainThread } = require('worker_threads');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Safety guard: this file is for the main thread only.
// Workers use the inlined WORKER_BOOT string (eval:true) and never load this file.
if (!isMainThread) { process.exit(2); }

// ---------------------------------------------------------------------------
// Worker bootstrap — embedded string constant, never written to /work.
// Passed to new Worker via eval:true so candidate code cannot replace it by
// writing to the work directory between cases.
// ---------------------------------------------------------------------------
const WORKER_BOOT = `
'use strict';
(function () {
  var _wt = require('worker_threads');
  var _port = _wt.parentPort;
  var _data = _wt.workerData;
  var code       = _data.code;
  var entryPoint = _data.entryPoint;
  var args       = _data.args;
  var nonce      = _data.nonce;

  // Poison the worker_threads module object.  Both require('worker_threads') and
  // process.getBuiltinModule('worker_threads') return the SAME cached object, so
  // nulling here neutralises every access path candidate code could use.
  _wt.parentPort = null;
  _wt.workerData = null;

  // Capture all mutable intrinsics as bound functions BEFORE new Function(code)(...).
  // A bound function is an exotic object: [[BoundCall]] invokes [[BoundTargetFunction]]
  // directly — no prototype chain lookup — so later replacement of
  // Function.prototype.call/apply, Promise.prototype.then, or
  // MessagePort.prototype.postMessage by candidate top-level IIFEs has no effect.
  var _Promise     = Promise;
  var _portPost    = _port.postMessage.bind(_port);
  var _funcApply   = Function.prototype.call.bind(Function.prototype.apply);
  var _promiseThen = Function.prototype.call.bind(Promise.prototype.then);
  var _isNativeError    = require('util').types.isNativeError;
  var _TypeErrorProto   = TypeError.prototype;
  var _RangeErrorProto  = RangeError.prototype;
  var _SyntaxErrorProto = SyntaxError.prototype;
  var _isPrototypeOf    = Function.prototype.call.bind(Object.prototype.isPrototypeOf);

  // Build result using null-prototype object literal (not Object.assign) so that
  // candidate replacement of Object.assign cannot forge the nonce.
  function postResult(msg) {
    var out = msg.ok
      ? { __proto__: null, ok: true,  value: msg.value, _nonce: nonce }
      : { __proto__: null, ok: false, error: msg.error, _nonce: nonce };
    _portPost(out);
  }

  // util.types.isNativeError uses V8 IsNativeError(): accepts genuine native Errors including
  // instances of user-defined subclasses (class CustomTypeError extends TypeError {}), and
  // rejects plain objects that merely have Error-like prototypes set via Object.setPrototypeOf.
  // _isPrototypeOf implements subclass-aware classification: CustomTypeError instances have
  // TypeError.prototype in their chain and are classified as TypeError (intentional).
  // globalThis.TypeError replacement has no effect because _TypeErrorProto was captured
  // before candidate code; constructor.name is not used at all.
  // SAME-REALM LIMITATION: Object.setPrototypeOf(realNativeError, TypeError.prototype) where
  // realNativeError is an existing native Error passes both checks and is classified as
  // TypeError; cannot be prevented without out-of-realm isolation.
  function errName(err, allowSyntax) {
    if (!_isNativeError(err)) return 'ThrownNonError';
    if (allowSyntax && _isPrototypeOf(_SyntaxErrorProto, err)) return 'SyntaxError';
    if (_isPrototypeOf(_TypeErrorProto,  err)) return 'TypeError';
    if (_isPrototypeOf(_RangeErrorProto, err)) return 'RangeError';
    return 'Error';
  }

  var fn;
  try {
    var m = { exports: {} };
    fn = new Function(
      'module', 'exports',
      code + '\\nreturn (typeof ' + entryPoint + ' !== "undefined") ? ' + entryPoint +
             ' : (module.exports["' + entryPoint + '"] || exports["' + entryPoint + '"] || undefined);'
    )(m, m.exports);
  } catch (err) {
    postResult({ ok: false, error: errName(err, true) });
    return;
  }

  if (typeof fn !== 'function') {
    postResult({ ok: false, error: 'InvalidReturn' });
    return;
  }

  // Use captured _Promise constructor so globalThis.Promise replacement has no effect.
  // Use captured _funcApply so Function.prototype.apply replacement has no effect.
  // Use captured _promiseThen so Promise.prototype.then replacement has no effect.
  var p = new _Promise(function (resolve, reject) {
    try { resolve(_funcApply(fn, null, args || [])); } catch (e) { reject(e); }
  });
  _promiseThen(p,
    function (value) {
      if (value === undefined) { postResult({ ok: false, error: 'InvalidReturn' }); return; }
      if (typeof value === 'number' && !Number.isFinite(value)) { postResult({ ok: false, error: 'InvalidReturn' }); return; }
      postResult({ ok: true, value: value });
    },
    function (err) {
      postResult({ ok: false, error: errName(err, false) });
    }
  );
})();
`;

// ---------------------------------------------------------------------------
// Main thread: orchestrate all cases sequentially
// ---------------------------------------------------------------------------
const argv = process.argv.slice(2);
if (argv.length < 2) { process.exit(2); }

const [workdir, entryPoint, caseTimeoutStr] = argv;
const caseTimeoutMs = Math.max(100, (parseFloat(caseTimeoutStr) || 2.0) * 1000);

let cases, solutionCode;
try {
  cases = JSON.parse(fs.readFileSync(path.join(workdir, 'cases.json'), 'utf8'));
  solutionCode = fs.readFileSync(path.join(workdir, 'solution.js'), 'utf8');
} catch (_) {
  process.exit(2);
}
// Delete cases.json immediately after reading it into memory.
// Workers are spawned only after this point, so candidate code has no path to read
// the full input list from disk — even if process.getBuiltinModule('fs') is accessible.
// Fail closed: abort if deletion fails or the file still exists after deletion.
const casesPath = path.join(workdir, 'cases.json');
try { fs.unlinkSync(casesPath); } catch (_) { process.exit(2); }
if (fs.existsSync(casesPath)) { process.exit(2); }

// Run one case in a fresh Worker. Returns the settled result dict (no _nonce field).
// Awaits full Worker termination before returning, so no candidate async work
// survives into the next case.
async function runCase(code, entry, args, timeoutMs) {
  const nonce = crypto.randomUUID();
  const worker = new Worker(WORKER_BOOT, {
    eval: true,
    workerData: { code, entryPoint: entry, args, nonce },
  });
  // Register the exit promise before event handlers so it is always ready.
  const exitPromise = new Promise(done => worker.once('exit', done));

  let settled = false;
  const result = await new Promise(resolve => {
    const settle = r => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(r);
    };

    const timer = setTimeout(
      () => settle({ ok: false, error: 'Timeout' }),
      timeoutMs
    );

    worker.on('message', msg => {
      // Strict schema: non-null object, boolean ok, correct nonce.
      if (msg === null || typeof msg !== 'object' || typeof msg.ok !== 'boolean') {
        settle({ ok: false, error: 'malformed result' });
      } else if (msg._nonce !== nonce) {
        // Missing or wrong nonce: message was not produced by the trusted bootstrap.
        settle({ ok: false, error: 'malformed result' });
      } else if (msg.ok === true && !Object.prototype.hasOwnProperty.call(msg, 'value')) {
        settle({ ok: false, error: 'malformed result' });
      } else if (msg.ok === false && typeof msg.error !== 'string') {
        settle({ ok: false, error: 'malformed result' });
      } else {
        // Strip _nonce before settling: it is an internal protocol detail.
        settle(msg.ok
          ? { ok: true, value: msg.value }
          : { ok: false, error: msg.error });
      }
    });
    worker.on('error', err => settle({
      ok: false,
      error: (err instanceof TypeError) ? 'TypeError' :
             (err instanceof RangeError) ? 'RangeError' :
             (err instanceof Error)      ? err.constructor.name : 'Error',
    }));
    worker.on('exit', exitCode => {
      // If already settled via message/error, this is a no-op.
      // Otherwise: exit with 0 and no message = adversarial process.exit().
      if (exitCode === 0) settle({ ok: false, error: 'exited without result' });
      else settle({ ok: false, error: `exited with code ${exitCode}` });
    });
  });

  // Terminate the Worker (no-op if it already exited) and wait until it is
  // fully gone before starting the next case.
  worker.terminate();
  await exitPromise;

  return result;
}

(async () => {
  const results = [];

  for (const c of cases) {
    const r = await runCase(solutionCode, entryPoint, c.args || [], caseTimeoutMs);
    results.push(r);
    if (r.error === 'Timeout') {
      while (results.length < cases.length) results.push({ ok: false, error: 'Timeout' });
      break;
    }
  }

  // Write authoritative results only after all Workers are terminated.
  // Unlink any existing file (removes symlinks without following them), then
  // create fresh with O_EXCL semantics via a rename from a temp file.
  const resultsPath = path.join(workdir, 'results.json');
  const tmpPath = resultsPath + '.tmp';
  try { fs.unlinkSync(resultsPath); } catch (_) {}
  try { fs.unlinkSync(tmpPath); } catch (_) {}
  fs.writeFileSync(tmpPath, JSON.stringify(results), { encoding: 'utf8', flag: 'wx' });
  fs.renameSync(tmpPath, resultsPath);

  process.exit(0); // do not wait for async work the candidate may have started
})().catch(() => process.exit(2));
