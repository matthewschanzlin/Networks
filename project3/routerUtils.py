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

    def keysCoalesce(key1, key2):
        ip1, cidr1 = key1.split("/")
        ip2, cidr2 = key2.split("/")
        bin1 = list(''.join(format(int(x), '08b') for x in ip1.split(".")))
        bin2 = list(''.join(format(int(x), '08b') for x in ip2.split(".")))
        idx = int(cidr1) - 1

        c1 = cidr1 == cidr2
        c2 = (bin1[idx] == '1') and (bin2[idx] == '0')
        c3 = (bin1[idx] == '0') and (bin2[idx] == '1')

        condition = c1 and (c2 or c3)
        
        return condition

    def handleCoalesce(keys, routes, forwardingInfo):
        key1 = keys[0]
        key2 = keys[1]
        ip, cidr = key1.split("/")
        binary = list(''.join(format(int(x), '08b') for x in ip.split(".")))
        binary[int(cidr) - 1] = '0'
        newipbinary = ''.join(binary)
        groupsOfEight = [newipbinary[i: i + 8] for i in range(0, len(newipbinary), 8)]
        for i in range(len(groupsOfEight)):
          groupsOfEight[i] = str(int(groupsOfEight[i], 2))

        newIp = '.'.join(groupsOfEight)
        newCidr = str(int(cidr) - 1)

        newKey = newIp + '/' + newCidr

        newNetmask = str(IPv4Network(newKey).netmask)
        updates1 = forwardingInfo[key1]
        updates2 = forwardingInfo[key2]

        for i in range(len(updates1)):
          for j in range(len(updates2)):
            if RouterUtils.info_matching((updates1[i], updates2[j])):
              newMsg = updates1[i]
              newMsg['msg']['network'] = newIp
              newMsg['msg']['netmask'] = newNetmask
              RouterUtils.handleUpdate(newKey, newMsg, routes, forwardingInfo)
              updates1.pop(i)
              updates2.pop(j)
              forwardingInfo[key1] = updates1
              forwardingInfo[key2] = updates2
              routes[newKey] = forwardingInfo[newKey][0]["src"]

              if len(forwardingInfo[key1]) == 0:
                del routes[key1]
                del forwardingInfo[key1]
              else:
                routes[key1] = forwardingInfo[key1][0]["src"]

              if len(forwardingInfo[key2]) == 0:
                del routes[key2]
                del forwardingInfo[key2]
              else:
                routes[key2] = forwardingInfo[key2][0]["src"]

              return True
        return False

    def formatUpdate(packet):
        update = {'src': packet[SRCE], 'dst': packet[DEST], 'type': UPDT}
        update[MESG] = {'localpref': packet[MESG][LPRF], 'ASPath': packet[MESG][APTH], 'network': packet[MESG][NTWK], 'netmask': packet[MESG][NMSK], 'origin': packet[MESG][ORIG], 'selfOrigin': packet[MESG][SORG]}
        return update

    def insertUpdate(packet, address, forwardingInfo):
        notInserted = True
        index = 0
        while notInserted and index < len(forwardingInfo):
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
