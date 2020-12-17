import json
import ipaddress
from ipaddress import IPv4Network

CUST = 'cust'

class RouterUtils:
    def sendPacketHelper(newPacket, key, sockets):
        newPacket["dst"] = key
        keyTemp = key.split(".")
        keyTemp[-1] = "1"
        keyTemp = ".".join(keyTemp)
        newPacket["src"] = keyTemp
        packetJSON = json.dumps(newPacket)
        packetJSON = packetJSON.encode("ASCII")
        sockets[key].send(packetJSON)

        return True

    def forwardData(sock, packet):
        packetJSON = json.dumps(packet)
        packetJSON = packetJSON.encode("ASCII")
        sock.send(packetJSON)
        return True

    def sendNoRoute(srcif, packet, sockets):
        srcifSplit = srcif.split(".")
        srcifSplit[-1] = "1"
        srcUs = ".".join(srcifSplit)
        noRouteMessage = {"src": srcUs, "dst": packet["src"], "type": "no route", "msg": {}}
        packetJSON = json.dumps(noRouteMessage)
        packetJSON = packetJSON.encode("ASCII")
        sockets[srcif].send(packetJSON)

        return False

    def getLongestPrefix(ports, sockets):
        sock = None
        longestPref = 0
        longestNetwork = ""
        for key in ports:
          pref = int(key.split("/")[1])

          if pref > longestPref:
            longestPref = pref
            longestNetwork = key
        if longestPref == 0:
          return None
        sock = sockets[ports[longestNetwork]]
        return sock


    def filterRelationships(ports, srcif, relations):
        keysToRemove = []
        if relations[srcif] != CUST:
          for key in ports:
            if relations[ports[key]] != CUST:
              keysToRemove.append(key)

        for key in keysToRemove:
          del ports[key]

        return ports

    def allPossible(dstAddress, routes):
        ports = {}

        for key in routes:
          if ipaddress.ip_address(dstAddress) in ipaddress.ip_network(key):
            ports[key] = routes.get(key)

        return ports

    def sameAttributes(msg1, msg2):
        return ((msg1['src'] == msg2['src']) and
                (msg1['msg']['localpref'] == msg2['msg']['localpref']) and
                (msg1['msg']['selfOrigin'] == msg2['msg']['selfOrigin']) and
                (msg1['msg']['ASPath'] == msg2['msg']['ASPath']) and
                (msg1['msg']['origin'] == msg2['msg']['origin']))

    def canCoalesceKey(key1, key2):
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


    def getCoalesce(routesAndUpdates):
        for key1, value1 in routesAndUpdates.items():
          for key2, value2 in routesAndUpdates.items():
            if (RouterUtils.canCoalesceKey(key1, key2)):
              for msg1 in value1:
                for msg2 in value2:
                  if RouterUtils.sameAttributes(msg1, msg2):
                    return [key1, key2]

        return None

    def handleCoalesce(key1, key2, routes, routesAndUpdates):
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
        updates1 = routesAndUpdates[key1]
        updates2 = routesAndUpdates[key2]

        for i in range(len(updates1)):
          for j in range(len(updates2)):
            if RouterUtils.sameAttributes(updates1[i], updates2[j]):
              newMsg = updates1[i]
              newMsg['msg']['network'] = newIp
              newMsg['msg']['netmask'] = newNetmask
              RouterUtils.placeUpdateInOrder(newKey, newMsg, routes, routesAndUpdates)
              updates1.pop(i)
              updates2.pop(j)
              routesAndUpdates[key1] = updates1
              routesAndUpdates[key2] = updates2
              routes[newKey] = routesAndUpdates[newKey][0]["src"]

              if len(routesAndUpdates[key1]) == 0:
                del routes[key1]
                del routesAndUpdates[key1]
              else:
                routes[key1] = routesAndUpdates[key1][0]["src"]

              if len(routesAndUpdates[key2]) == 0:
                del routes[key2]
                del routesAndUpdates[key2]
              else:
                routes[key2] = routesAndUpdates[key2][0]["src"]

              return True
        return False


    def placeUpdateInOrder(networkAddress, packet, routes, routesAndUpdates):
        newPacket = {"type": "update", "src": packet["src"], "dst": packet["dst"],
                     "msg": {"network": packet["msg"]["network"], "netmask": packet["msg"]["netmask"],
                             "localpref": packet["msg"]["localpref"], "ASPath": packet["msg"]["ASPath"],
                             "origin": packet["msg"]["origin"], "selfOrigin": packet["msg"]["selfOrigin"]}}
        if routesAndUpdates.get(networkAddress) == None:
          routesAndUpdates[networkAddress] = [newPacket]
          return True

        for i in range(len(routesAndUpdates[networkAddress])):
          if RouterUtils.isBestPath(newPacket, routesAndUpdates[networkAddress][i]):
            routesAndUpdates[networkAddress].insert(i, newPacket)
            return True
        routesAndUpdates[networkAddress].append(newPacket)

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

    def calculateNetAddress(address, mask, maskConvTable):
        maskVal = 0
        maskArr = mask.split(".")
        for i in range(len(maskArr)):
        if (maskConvTable.get(maskArr[i]) == None):
         raise KeyError
        maskVal += maskConvTable[maskArr[i]]

        return address + "/" + str(maskVal)
