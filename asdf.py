#!/usr/bin/env python3
import hashlib
import re
import struct


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


def vroom(logline):
    desysed = unwrap_syslog(logline)
    ip, path, referrer, ua = parse_httpd_log(desysed)
    bucket, zeros = compress(ip, ua)
    return path, referrer, bucket, zeros
