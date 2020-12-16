import json

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

    def forwardData(self, sock, packet):
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
