#!/usr/bin/env python3
import functools
import http.server
import os.path
import queue
import socketserver
import sys
import threading
import traceback

from asdf import unwrap_syslog, parse_httpd_log, compress, run_lines, postit

regrets = []

B = lambda m: f'\u001b[1m{m}\u001b[0m'
r = lambda m: f'\u001b[31m{m}\u001b[0m'
g = lambda m: f'\u001b[32m{m}\u001b[0m'
y = lambda m: f'\u001b[33m{m}\u001b[0m'
c = lambda m: f'\u001b[36m{m}\u001b[0m'

def with_last(l):
    for i, item in enumerate(l):
        yield item, i == len(l) - 1

def hope(that, will, given, desire):
    def e():
        print(f'{r(B("×"))} {B(that.__name__)}({", ".join(map(repr, given))}) could not {B(will)} when:')
        regrets.append(that.__name__)
    try:
        outcome = that(*given)
    except Exception as cursed:
        e()
        stack = traceback.extract_tb(cursed.__traceback__.tb_next)
        current_filename = None
        for frame, last in with_last(stack):
            if frame.filename != current_filename:
                current_filename = frame.filename
                print(f'  {y("↬")} in {r(os.path.relpath(frame.filename))},')
            print(f'      {c(frame.name)} {"tried" if last else "ran"}')
            print(f' {last and "💥" or " "} {frame.lineno: 3d}| {B(frame.line)}')
        print(f'  which {r("raised")} a {B(cursed)}')
        print(f'    » {B(cursed)}')
        return print()
    else:
        if outcome != desire:
            e()
            print(f'    we found {r(B(outcome))!r}')
            print(f'  instead of {B(desire)!r}')
            return print()
    print(f'{g(B("✓"))} {B(that.__name__)} really did {B(will)}')

def looping(that):
    @functools.wraps(that)
    def looped_that(*given):
        return tuple(that(given))
    return looped_that


class HttpFn(object):
    def __init__(self, get_fn):
        self.get_fn = get_fn
        self.q = queue.SimpleQueue()

    def __enter__(self):

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(_self):
                assert _self.headers['content-type'] == 'application/json', _self.headers
                body = _self.rfile.read(int(_self.headers['content-length']))
                _self.send_response(http.HTTPStatus.ACCEPTED)
                _self.send_header("Content-Length", f'{0}')
                _self.end_headers()
                self.q.put(body)

        server = socketserver.TCPServer(('', 0), Handler)
        fn = self.get_fn(*server.server_address)
        fn(None)  # start up the generator

        @functools.wraps(fn)
        def uhh(*args):
            with server:
                t = threading.Thread(target=server.serve_forever)
                t.daemon = True
                t.start()
                fn(*args)
            return self.q.get(timeout=1)

        return uhh

    def __exit__(self, *_errstuff):
        assert self.q.empty(), 'wat, queue not empty'


hope(unwrap_syslog, will='strip the syslog bit before the message',
    given=('2001-01-01T00:00:01.000Z host service[12345]: some message\n',),
    desire='some message\n')


hope(unwrap_syslog, will='not explode on an empty message',
    given=('2001-01-01T00:00:01.000Z host service[49065]: \n',),
    desire='\n')


hope(unwrap_syslog, will='handle a real log line we car about',
    given=('2020-11-09T06:19:24.610Z openbsd-dev httpd[81336]: hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',),
    desire='hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n')


hope(parse_httpd_log, will='extract the parts',
    given=('servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "referrer" "ua"\n',),
    desire=('127.0.0.1', '/path', 'referrer', 'ua'))


hope(parse_httpd_log, will='capture quotes in the UA',
    given=('servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "referrer" "u"a"\n',),
    desire=('127.0.0.1', '/path', 'referrer', 'u"a'))


hope(parse_httpd_log, will='handle http 1.0 proto',
    given=('servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.0" 200 0 "referrer" "ua"\n',),
    desire=('127.0.0.1', '/path', 'referrer', 'ua'))


hope(parse_httpd_log, will='handle http absent referrer',
    given=('servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "" "ua"\n',),
    desire=('127.0.0.1', '/path', '', 'ua'))


hope(parse_httpd_log, will='handle a sample line from the real deal',
    given=('hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',),
    desire=('192.168.1.111', '/aaaaab/bzz.gif', 'http://192.168.8.88/aaaaaa/bzz.gif', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0'))


hope(compress, will='turn an ip and UA into a bucket and leading-zero count',
    given=('192.168.1.111', 'ua'),
    desire=(3974, 6))


hope(compress, will='turn a different ip into a different bucket & zero count',
    given=('192.168.1.112', 'ua'),
    desire=(2302, 1))


hope(compress, will='turn a different ua into a different bucket & zero count',
    given=('192.168.1.111', 'ub'),
    desire=(683, 1))


hope(compress, will='compress a long ua just fine',
    given=('192.168.1.111', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0'),
    desire=(1194, 2))


hope(compress, will='also work with an empty UA',
    given=('0.0.0.0', ''),
    desire=(1378, 1))


hope(looping(run_lines), will='yield a compressed line',
    given=['2020-11-09T06:19:24.610Z openbsd-dev httpd[81336]: hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/this/page" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n'],
    desire=('["v1", "ok", "/aaaaab/bzz.gif", "http://192.168.8.88/this/page", 1194, 2]',))


hope(looping(run_lines), will='yield multiple compressed lines',
    given=(x for x in [  # generatorize
        '2020-11-09T06:19:24.610Z openbsd-dev httpd[81336]: hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/this/page" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',
        '2020-11-09T06:19:24.610Z openbsd-dev httpd[81336]: hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/this/page" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',
    ]),
    desire=(
        '["v1", "ok", "/aaaaab/bzz.gif", "http://192.168.8.88/this/page", 1194, 2]',
        '["v1", "ok", "/aaaaab/bzz.gif", "http://192.168.8.88/this/page", 1194, 2]',
    ))


with HttpFn(lambda ip, port: postit(f'http://{ip}:{port}').send) as p:
    hope(p, will='get our empty string back', given=(b'""', ), desire=b'""')


with HttpFn(lambda ip, port: postit(f'http://{ip}:{port}').send) as p:
    hope(p, will='send data or w/e', given=(b'["a", 1]', ), desire=b'["a", 1]')


if len(regrets) > 0:
    sys.exit(1)
