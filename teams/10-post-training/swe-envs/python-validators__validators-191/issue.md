# IPv4 validator accepts any number of 0's in a segment

Upstream issue: https://github.com/python-validators/validators/issues/190 (opened by @tomguyatt on 2021-04-29). Text copied unchanged.

**Version: 0.18.2**

The `ipv4` validator only tests that:

- The number of dot-delimited groups is 4
- Each group represents a 'digit'
- The value of each digit is `>= 0` & `< 256`

Therefore a segment can contain as many zeroes as you like, and it'll still validate:

```python
In [18]: validators.ipv4("00000.00000.00000.00000")
Out[18]: True
```

```python
In [19]: validators.ipv4("192.168.123.000000000")
Out[19]: True
```
