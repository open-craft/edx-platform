"""
Monkey patch implementation of the quote and unquote functions used in admin:

https://github.com/django/django/blob/de81676b51e4dad510ef387c3ae625f9091fe57f/django/contrib/admin/utils.py#L66

Remove once we upgrade to Juniper, which uses a Django version with these changes.
"""
import re
import struct
from django.contrib.admin import options

__QUOTE__NAME = 'quote__original'
__UNQUOTE__NAME = 'unquote__original'


QUOTE_MAP = {struct.unpack('b', c)[0]: '_%02X' % struct.unpack('b', c) for c in b'":/_#?;@&=+$,"[]<>%\n\\'}
UNQUOTE_MAP = {v: chr(k) for k, v in QUOTE_MAP.items()}
UNQUOTE_RE = re.compile('_(?:%s)' % '|'.join([x[1:] for x in UNQUOTE_MAP]))


def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' and similarly problematic characters.
    Similar to urllib.parse.quote(), except that the quoting is slightly
    different so that it doesn't get automatically unquoted by the Web browser.
    """
    return s.translate(QUOTE_MAP) if isinstance(s, str) else s


def unquote(s):
    """Undo the effects of quote()."""
    return UNQUOTE_RE.sub(lambda m: UNQUOTE_MAP[m[0]], s)


def patch():
    setattr(options, 'quote', quote)
    setattr(options, 'unquote', unquote)
