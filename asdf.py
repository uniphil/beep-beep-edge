#!/usr/bin/env python3
import hashlib
import json
import re
import struct
import urllib.request


def unwrap_syslog(line):
    _, rest = line.split(']: ', 1)
    return rest


def parse_httpd_log(line):
    m = re.match(r'^\w+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) \-.*\- \[.*\] "GET (.*) HTTP/1\.[01]" 200 0 "(.*?)" "(.*)"\n$', line)
    return m.groups()


def compress(ip, ua):
    ip_bytes = bytes(map(int, ip.split('.')))
    bits = hashlib.blake2b(ua.encode(), digest_size=4, key=ip_bytes)
    as_uint, = struct.unpack('I', bits.digest())
    bucket = as_uint & 0b111111111111  # 12
    clz = 20 - (as_uint >> 12).bit_length() + 1  # never zero
    return bucket, clz


def run_lines(lines):
    for line in lines:
        if line.strip() == '':
            continue
        desysed = unwrap_syslog(line)
        ip, path, referrer, ua = parse_httpd_log(desysed)
        bucket, zeros = compress(ip, ua)
        yield json.dumps(['v1', 'ok', path, referrer, bucket, zeros])


def postit(url):
    r = urllib.request.Request(url, b'', {'Content-Type': 'application/json'})
    while True:
        r.data = yield
        with urllib.request.urlopen(r, timeout=2) as resp:
            if resp.status != 202:
                raise Exception('ohno', resp.status)


if __name__ == '__main__':
    import fileinput
    import os
    post_office = postit(os.environ['DESTINATION'])
    next(post_office)  # unfortunate init
    for compressed in run_lines(fileinput.input()):
        post_office.send(compressed)
