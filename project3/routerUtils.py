import json
import ipaddress
from ipaddress import IPv4Network

CUST = 'cust'
IGP = "IGP"
EGP = "EGP"
UNK = "UNK"
MESG = "msg"
NTWK = "network"
NMSK = "netmask"
ORIG = "origin"
LPRF = "localpref"
APTH = "ASPath"
SORG = "selfOrigin"
SRCE = "src"
DEST = "dst"
UPDT = "update"

t1 = lambda p1, p2: p1[MESG][LPRF] > p2[MESG][LPRF]
t2 = lambda p1, p2: p1[MESG][LPRF] < p2[MESG][LPRF]
t3 = lambda p1, p2: p1[MESG][SORG] and not(p2[MESG][SORG])
t4 = lambda p1, p2: not(p1[MESG][SORG]) and (p2[MESG][SORG])
t5 = lambda p1, p2: len(p1[MESG][APTH]) < len(p2[MESG][APTH])
t6 = lambda p1, p2: len(p1[MESG][APTH]) > len(p2[MESG][APTH])
t7 = lambda p1, p2: (p1[MESG][ORIG] == IGP) and (not(p2[MESG][ORIG]) == IGP)
t8 = lambda p1, p2: (not(p1[MESG][ORIG]) == IGP) and (p2[MESG][ORIG] == IGP)
t9 = lambda p1, p2: (p1[MESG][ORIG] == EGP) and (not(p2[MESG][ORIG]) == EGP)
t10 = lambda p1, p2: (not(p1[MESG][ORIG]) == EGP) and (p2[MESG][ORIG] == EGP)
t11 = lambda p1, p2: (p1[MESG][ORIG] == UNK) and (not(p2[MESG][ORIG]) == UNK)
t12 = lambda p1, p2: (not(p1[MESG][ORIG]) == UNK) and (p2[MESG][ORIG] == UNK)
t13 = lambda p1, p2: ipaddress.IPv4Address(p1[SRCE]) < ipaddress.IPv4Address(p2[SRCE])

class RouterUtils:
    format_packet = lambda srcif, p: {'src': '.'.join(srcif.split('.')[:-1] + ['1']), 'dst': p['src'], 'type': 'no route', 'msg': {}}
    true_conditions = lambda p1, p2: [t1(p1,p2), t3(p1,p2), t5(p1,p2), t7(p1,p2), t9(p1,p2), t11(p1,p2), t13(p1,p2)]
    false_conditions = lambda p1, p2: [t2(p1,p2), t4(p1,p2), t6(p1,p2), t8(p1,p2), t10(p1,p2), t12(p1,p2), (not t13(p1,p2))]

    def specialForward(srcif, packet, type, sockets, relations):
        forward_packet = {'src': None, 'dst': None, 'type': type, 'msg': packet['msg']}
        if (relations[packet['src']] == CUST):
            RouterUtils.forwardSocks(srcif, forward_packet, sockets)
        else:
            RouterUtils.forwardRelations(srcif, forward_packet, relations, sockets)

    def forwardSocks(srcif, packet, sockets):
        for sock in sockets:
            if sock != srcif:
                packet['src'] = '.'.join(sock.split('.')[:-1] + ['1'])
                packet['dst'] = sock
                sockets[sock].send(json.dumps(packet).encode('ASCII'))

    def forwardRelations(srcif, packet, relations, sockets):
        for relation in relations:
            if (relations[relation] == CUST) and (relation != srcif):
                packet['src'] = '.'.join(relation.split('.')[:-1] + ['1'])
                packet['dst'] = relation
                sockets[relation].send(json.dumps(packet).encode('ASCII'))

    def check_match(item1, item2, matching_fields):
        return len(list(filter(lambda field: item1[field] == item2[field], matching_fields))) == len(matching_fields)

    def info_matching(info):
        src = RouterUtils.check_match(info[0], info[1], ['src'])
        fields = RouterUtils.check_match(info[0]['msg'], info[1]['msg'], ['localpref', 'selfOrigin', 'ASPath', 'origin'])
        return src and fields

    def convertToBits(address):
        bits = ''
        comparator = '08b'

        for part in address.split("/")[0].split('.'):
            bits +=  format(int(part), comparator)

        return bits


    def build_comparison_bits(bits):
        comparison_bits = ['', '']
        comparison_bits[0] = RouterUtils.convertToBits(bits[0])
        comparison_bits[1] = RouterUtils.convertToBits(bits[1])
        return comparison_bits

    def coalescableAddresses(address1, address2):
        comparison_bit = int(address1.split("/")[1]) - 1
        comparison_bits = RouterUtils.build_comparison_bits([address1, address2])
        c1 = address1.split("/")[1] == address2.split("/")[1]
        c2 = comparison_bits[0][comparison_bit] != comparison_bits[1][comparison_bit]
        return c1 and c2

    def manageCoalesceAddress(address, routes, forwardingInfo, update):
        coalescable = len(forwardingInfo[address]) > 0
        if coalescable:
            routes[address] = forwardingInfo[address][0][SRCE]
            forwardingInfo[address] = update
        else:
            forwardingInfo.pop(address, None)
            routes.pop(address, None)




    def maskAddress(key):
        binary = list(RouterUtils.convertToBits(key.split('/')[0]))
        binary[int(key.split('/')[1]) - 1] = '0'
        return ''.join(binary)

    def buildNewAddress(key):
        newipbinary = RouterUtils.maskAddress(key)
        firstOctet = newipbinary[0:8]
        secondOctet = newipbinary[8:16]
        thirdOctet = newipbinary[16:24]
        fourthOctet = newipbinary[24:32]
        binaryNums = [firstOctet, secondOctet, thirdOctet, fourthOctet]
        convert = lambda n: str(int(n, 2))
        decimalNums = list(map(convert, binaryNums))
        newAddress = '.'.join(decimalNums) + '/' + str(int(key.split('/')[1]) - 1)
        return newAddress

    def handleCoalesce(addresses, routes, forwardingInfo):
        forwardingInfo1 = forwardingInfo[addresses[0]]
        forwardingInfo2 = forwardingInfo[addresses[1]]
        newAddress = RouterUtils.buildNewAddress(addresses[0])

        for index1 in range(0, len(forwardingInfo1)):
            updatespacket = forwardingInfo1[index1]
            updatespacket[MESG][NMSK] = str(IPv4Network(newAddress).netmask)
            updatespacket[MESG][NTWK] = newAddress.split('/')[0]

            for index2 in range(0, len(forwardingInfo2)):
                if RouterUtils.info_matching((forwardingInfo1[index1], forwardingInfo2[index2])):
                    RouterUtils.handleUpdate(newAddress, updatespacket, routes, forwardingInfo)
                    forwardingInfo1.pop(index1)
                    forwardingInfo2.pop(index2)
                    RouterUtils.manageCoalesceAddress(addresses[0], routes, forwardingInfo, forwardingInfo1)
                    RouterUtils.manageCoalesceAddress(addresses[1], routes, forwardingInfo, forwardingInfo2)
                    routes[newAddress] = forwardingInfo[newAddress][0][SRCE]
                    return True
        return False








    def formatUpdate(packet):
        update = {'src': packet[SRCE], 'dst': packet[DEST], 'type': UPDT}
        update[MESG] = {'localpref': packet[MESG][LPRF], 'ASPath': packet[MESG][APTH], 'network': packet[MESG][NTWK], 'netmask': packet[MESG][NMSK], 'origin': packet[MESG][ORIG], 'selfOrigin': packet[MESG][SORG]}
        return update

    def insertUpdate(update, address, forwardingInfo):
        notInserted = True
        index = 0
        while notInserted and index < len(forwardingInfo[address]):
            if RouterUtils.chooseNextPath(update, forwardingInfo[address][index]):
                forwardingInfo[address].insert(index, update)
                notInserted = False
            else:
                index += 1

        if notInserted:
            forwardingInfo[address].append(update)
        return True

    def handleUpdate(address, packet, routes, forwardingInfo):
        update = RouterUtils.formatUpdate(packet)
        check = lambda fi, na, u: [u] if na not in fi else fi[na]
        if address not in forwardingInfo:
            forwardingInfo[address] = [update]
        else:
            RouterUtils.insertUpdate(update, address, forwardingInfo)

        return True

    def chooseNextPath(next_path, current_path):
        for i in range(0, len(RouterUtils.true_conditions(next_path, current_path))):
            if RouterUtils.true_conditions(next_path, current_path)[i]:
                return True
            elif RouterUtils.false_conditions(next_path, current_path)[i]:
                return False
        return False

    def configureNetmask(address, mask):
        netmaskLength = lambda s: {'0': 0, '128': 1, '192': 2, '224': 3, '240': 4, '248': 5, '252': 6, '254': 7, '255': 8}[s]
        netmask = sum(list(map(netmaskLength, mask.split('.'))))
        address_string = '/'.join([address, str(netmask)])
        return address_string
