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
s.connect((HOSTNAME, PORT))
s.send('cs3700fall2020 HELLO 001699953\n')
bits = 1024
finding = True
flag = ''
count = 0

while finding:
    more_data = True
    data = ''
    while more_data:
        this_data = s.recv(bits)
        if len(this_data) == 0:
            more_data = False
        else:
            data += this_data

    data_pieces = data.split(' ')
    print('LEN ', len(data_pieces))
    message = data_pieces[1]
    if message == 'FIND':
        symbol = data_pieces[2]
        symbols = data_pieces[3]
        count = symbols.count(symbol)
        response = 'cs3700fall2020 COUNT {}\n'.format(str(count))
        print('response ', response)
        s.send(response)
    elif message == 'BYE':
        finding = False
        flag = data_pieces[2]
        print('FLAG ', flag)
    print('LOOP BACK')
print('FLAG ', flag)
