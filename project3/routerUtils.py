
class RouterUtils:
    def sendPacketHelper(self, newPacket, key, sockets):
        newPacket["dst"] = key
        keyTemp = key.split(".")
        keyTemp[-1] = "1"
        keyTemp = ".".join(keyTemp)
        newPacket["src"] = keyTemp
        packetJSON = json.dumps(newPacket)
        packetJSON = packetJSON.encode("ASCII")
        sockets[key].send(packetJSON)

        return True
