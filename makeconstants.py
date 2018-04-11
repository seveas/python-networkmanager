# Reads the Networkmanager headers and spits out the enums as a series of
# python variables.

import re

enum_regex = re.compile(r'typedef enum(?:\s+[a-zA-Z]+)?\s*\{(.*?)\}', re.DOTALL)
comment_regex = re.compile(r'/\*.*?\*/', re.DOTALL)
headers = [ '/usr/include/libnm/nm-dbus-interface.h',
           '/usr/include/NetworkManager/NetworkManagerVPN.h',
           '/usr/include/libnm-glib/nm-secret-agent.h']

for h in headers:
    for enum in enum_regex.findall(open(h).read()):
        enum = comment_regex.sub('', enum)
        last = -1
        for key in enum.split(','):
            if not key.strip():
                continue
            if '=' in key:
                key, val = key.split('=')
                val = eval(val.replace('LL',''))
            else:
                val = last + 1
            key = key.strip()
            print('%s = %d' % (key, val))
            last = val
