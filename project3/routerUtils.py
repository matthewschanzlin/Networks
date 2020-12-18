import json
import ipaddress
from ipaddress import IPv4Network

CUST = 'cust'

class RouterUtils:
    format_packet = lambda srcif, p: {'src': '.'.join(srcif.split('.')[:-1] + ['1']), 'dst': p['src'], 'type': 'no route', 'msg': {}}

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
        if (cidr1 == cidr2):
          bin1 = list(''.join(format(int(x), '08b') for x in ip1.split(".")))
          bin2 = list(''.join(format(int(x), '08b') for x in ip2.split(".")))
          idx = int(cidr1) - 1

          if ((bin1[idx] == '1') and (bin2[idx] == '0')):
            return True
          if ((bin1[idx] == '0') and (bin2[idx] == '1')):
            return True
        return False

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
              RouterUtils.placeUpdateInOrder(newKey, newMsg, routes, forwardingInfo)
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

    def placeUpdateInOrder(networkAddress, packet, routes, forwardingInfo):
        newPacket = {"type": "update", "src": packet["src"], "dst": packet["dst"],
                     "msg": {"network": packet["msg"]["network"], "netmask": packet["msg"]["netmask"],
                             "localpref": packet["msg"]["localpref"], "ASPath": packet["msg"]["ASPath"],
                             "origin": packet["msg"]["origin"], "selfOrigin": packet["msg"]["selfOrigin"]}}
        if forwardingInfo.get(networkAddress) == None:
          forwardingInfo[networkAddress] = [newPacket]
          return True

        for i in range(len(forwardingInfo[networkAddress])):
          if RouterUtils.isBestPath(newPacket, forwardingInfo[networkAddress][i]):
            forwardingInfo[networkAddress].insert(i, newPacket)
            return True
        forwardingInfo[networkAddress].append(newPacket)

        return True

    def isBestPath(newPacket, oldPacket):
        msg = 'msg'
        localpref = 'localpref'
        selfOrigin = 'selfOrigin'
        ASPATH = 'ASPath'
        origin = 'origin'

        if (newPacket[msg][localpref] > oldPacket[msg][localpref]):
            return True
        elif (newPacket[msg][localpref] < oldPacket[msg][localpref]):
            return False

        if (newPacket[msg][selfOrigin] and not(oldPacket[msg][selfOrigin])):
            return True
        elif (not(newPacket[msg][selfOrigin]) and (oldPacket[msg][selfOrigin])):
            return False

        if (len(newPacket[msg][ASPATH]) < len(oldPacket[msg][ASPATH])):
            return True
        elif (len(newPacket[msg][ASPATH]) > len(oldPacket[msg][ASPATH])):
            return False

        if ((newPacket[msg][origin] == "IGP") and (not(oldPacket[msg][origin]) == "IGP")):
            return True
        elif ((not(newPacket[msg][origin]) == "IGP") and (oldPacket[msg][origin] == "IGP")):
            return False

        if ((newPacket[msg][origin] == "EGP") and (not(oldPacket[msg][origin]) == "EGP")):
            return True
        elif ((not(newPacket[msg][origin]) == "EGP") and (oldPacket[msg][origin] == "EGP")):
            return False

        if ((newPacket[msg][origin] == "UNK") and (not(oldPacket[msg][origin]) == "UNK")):
            return True
        elif ((not(newPacket[msg][origin]) == "UNK") and (oldPacket[msg][origin] == "UNK")):
            return False

        newIP = ipaddress.IPv4Address(newPacket['src'])
        oldIP = ipaddress.IPv4Address(oldPacket['src'])
        return (newIP < oldIP)

    def configureNetmask(address, mask):
        netmaskLength = lambda s: {'0': 0, '128': 1, '192': 2, '224': 3, '240': 4, '248': 5, '252': 6, '254': 7, '255': 8}[s]
        netmask = sum(list(map(netmaskLength, mask.split('.'))))
        address_string = '/'.join([address, str(netmask)])
        return address_string
