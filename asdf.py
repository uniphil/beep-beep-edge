#!/usr/bin/env python3
import re


def unwrap_syslog(line):
    _, rest = line.split(']: ', 1)
    return rest


def parse_httpd_log(line):
    m = re.match(r'^\w+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) \-.*\- \[.*\] "GET (.*) HTTP/1\.[01]" 200 0 "(.*?)" "(.*)"\n$', line)
    return m.groups()


def test():
    import traceback
    import os.path
    mistakes = []

    B = lambda m: f'\u001b[1m{m}\u001b[0m'
    r = lambda m: f'\u001b[31m{m}\u001b[0m'
    g = lambda m: f'\u001b[32m{m}\u001b[0m'
    y = lambda m: f'\u001b[33m{m}\u001b[0m'
    c = lambda m: f'\u001b[36m{m}\u001b[0m'

    def with_last(l):
        for i, item in enumerate(l):
            yield item, i == len(l) - 1

    def hope(that, will, given, desire):
        e = lambda: print(f'{r(B("×"))} {B(that.__name__)} could not {B(will)} when:')
        try:
            outcome = that(given)
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
            print(f'  which {r("raised")} a {B(repr(cursed))}')
            print(f'    » {B(cursed)}')
            return print()
        else:
            if outcome != desire:
                e()
                print(f'    we found {r(B(repr(outcome)))}')
                print(f'  instead of {B(repr(desire))}')
                return print()
        print(f'{g(B("✓"))} {B(that.__name__)} really did {B(will)}')

    hope(unwrap_syslog, will='strip the syslog bit before the message',
        given='2001-01-01T00:00:01.000Z host service[12345]: some message\n',
        desire='some message\n')

    hope(unwrap_syslog, will='not explode on an empty message',
        given='2001-01-01T00:00:01.000Z host service[49065]: \n',
        desire='\n')

    hope(unwrap_syslog, will='handle a real log line we car about',
        given='2020-11-09T06:19:24.610Z openbsd-dev httpd[81336]: hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',
        desire='hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n')

    hope(parse_httpd_log, will='extract the parts',
        given='servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "referrer" "ua"\n',
        desire=('127.0.0.1', '/path', 'referrer', 'ua'))

    hope(parse_httpd_log, will='capture quotes in the UA',
        given='servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "referrer" "u"a"\n',
        desire=('127.0.0.1', '/path', 'referrer', 'u"a'))

    hope(parse_httpd_log, will='handle http 1.0 proto',
        given='servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.0" 200 0 "referrer" "ua"\n',
        desire=('127.0.0.1', '/path', 'referrer', 'ua'))

    hope(parse_httpd_log, will='handle http absent referrer',
        given='servername 127.0.0.1 - - [01/Jan/2001:00:00:01 -0500] "GET /path HTTP/1.1" 200 0 "" "ua"\n',
        desire=('127.0.0.1', '/path', '', 'ua'))

    hope(parse_httpd_log, will='handle a sample line from the real deal',
        given='hello 192.168.1.111 - - [09/Nov/2020:01:19:24 -0500] "GET /aaaaab/bzz.gif HTTP/1.1" 200 0 "http://192.168.8.88/aaaaaa/bzz.gif" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0"\n',
        desire=('192.168.1.111', '/aaaaab/bzz.gif', 'http://192.168.8.88/aaaaaa/bzz.gif', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.88; rv:888.0) Gecko/20100101 Firefox/88.0'))


if __name__ == '__main__':
    test()