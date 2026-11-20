function camelToSnake(s) {
  if (typeof s !== 'string') throw new TypeError('input must be a string');
  if (s.length === 0) throw new RangeError('input must not be empty');
  let result = '';
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch >= 'A' && ch <= 'Z') {
      result += '_' + ch.toLowerCase();
    } else {
      result += ch;
    }
  }
  // Remove the leading underscore only if it was inserted because the FIRST CHARACTER
  // of the input was uppercase.  An original leading underscore in the input must be
  // preserved: e.g. "_foo" -> "_foo", "_Foo" -> "__foo", "__Foo" -> "___foo".
  return (s[0] >= 'A' && s[0] <= 'Z') ? result.slice(1) : result;
}
