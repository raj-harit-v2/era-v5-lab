# `canonicalize_url` should not accept whitespace at the begin of an URI

Upstream issue: https://github.com/scrapy/w3lib/issues/132 (opened by @abmxer on 2015-11-24). Text copied unchanged.

Accepting whitespace in the begin of URI introduces a crawling issue. Unique URIs are generated on each depth and crawler gets in a loop. 

When a URI is extracted and begins with whitespace it is being considered a relative URI and its concatenated at the end of current URI, which leads to unique URI on each crawler depth. 

But, accordingly to RFC2396 [ Page 38], the scheme part of an URI should begin with an ALPHA character. 

> "The syntax for URI scheme has been changed to require that all schemes begin with an alpha character." 

After further investigation, the core python `urlparse` function doesn't follow RFC strictly, they consider some rules. Like on Python 3.5 they say: 

> "Changed in version 3.3: The fragment is now parsed for all URL schemes (unless allow_fragment is false), in accordance with RFC 3986. Previously, a whitelist of schemes that support fragments existed." 

However a better implementation should be in accordance with RFC 3986 (which is an update of RFC2396 mentioned before), the `urlparse` should not accept whitespace at the begin of URI. 

When compared to the with Ruby implementation of RFC 2396,  they don't allow whitespace at the begin of absolute or relative URIs and throws an exception "bad URI(is not URI?)".

In order to fix that on Scrapy level, I suggest the following. 

In `scrapy/utils/url.py` add at the begin of `canonicalize_url`:

```
if re.match('[a-zA-Z]', url[:1]) == None:
    raise ValueError('Bad URI (is not a valid URI?)')
```

An a test in `tests/test_utils_url.py`:

```
def test_rfc2396_scheme_should_begin_with_alpha(self):
    self.assertRaises(ValueError, canonicalize_url," http://www.example.com")
```

But raising an exception breaks a lot of tests and can introduce unexpected behaviors. You could simple `.strip()` url, but won't make it RFC compliant.
