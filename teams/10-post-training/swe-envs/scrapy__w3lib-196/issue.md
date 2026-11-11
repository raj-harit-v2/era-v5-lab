# safe_url_string URL-encodes already-encoded username and password, breaking idempodency

Upstream issue: https://github.com/scrapy/w3lib/issues/187 (opened by @andersk on 2022-08-14). Text copied unchanged.

The documentation claims that calling `safe_url_string` on an already “safe” URL will return the URL unmodified, but this breaks when the username or password include `%`.

```python
>>> url = 'http://%25user:%25pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%2525user:%2525pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%252525user:%252525pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%25252525user:%25252525pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%2525252525user:%2525252525pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%252525252525user:%252525252525pass@host'
>>> url = w3lib.url.safe_url_string(url); url
'http://%25252525252525user:%25252525252525pass@host'
```
