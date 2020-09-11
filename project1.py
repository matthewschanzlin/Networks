import socket
import sys

PORT = 27993
HOSTNAME = ''
NUID = 0
args = sys.argv
use_ssl = False

need_hostname = True
check_port = False
for i in range(1, len(args)):
    arg = args[i]
    if arg == '-p':
        check_port = True
    elif arg == '-s':
        use_ssl = True
    elif check_port:
        check_port = False
        PORT = int(arg)
    elif need_hostname:
        need_hostname = False
        HOSTNAME = arg
    else:
        NUID = int(arg)

print('PORT ', PORT)
print('use_ssl ', use_ssl)
print('HOSTNAME ', HOSTNAME)
print('NUID ', NUID)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOSTNAME, PORT))
