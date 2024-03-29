import socket
import sys
import ssl

PORT = 0
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
        NUID = arg

print('PORT ', PORT)
print('use_ssl ', use_ssl)
print('HOSTNAME ', HOSTNAME)
print('NUID ', NUID)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOSTNAME, PORT))
if use_ssl:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    s = context.wrap_socket(s, server_side=False, server_hostname=HOSTNAME)
print('SOCKET ', s)
s.send(bytes('cs3700fall2020 HELLO {}\n'.format(NUID)))

bits = 1024
finding = True
flag = ''
count = 0

while finding:
    more_data = True
    data = ''
    while more_data:
        this_data = s.recv(bits)
        data += this_data
        if '\n' in this_data:
            more_data = False

    data_pieces = data.split(' ')
    message = data_pieces[1]

    if message == 'FIND':
        symbol = data_pieces[2]
        symbols = data_pieces[3]
        count = symbols.count(symbol)
        response = 'cs3700fall2020 COUNT {}\n'.format(str(count))
        s.send(bytes(response))

    elif message == 'BYE':
        finding = False
        flag = data_pieces[2]

print('FLAG ', flag)
