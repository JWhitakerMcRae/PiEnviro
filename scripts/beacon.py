#!/usr/bin/python
from bluetooth.ble import BeaconService


class Beacon(object):
    """
    TODO
    """

    def __init__(self, address, data):
        """
        TODO
        """
        self._address = address
        self._uuid = data[0]
        self._major = data[1]
        self._minor = data[2]
        self._power = data[3]
        self._rssi = data[4]

    def __str__(self):
        """
        TODO
        """
        return 'Beacon: address:{ADDR} uuid:{UUID} major:{MAJOR} minor:{MINOR} txpower:{POWER} rssi:{RSSI}'\
            .format(ADDR=self._address, UUID=self._uuid, MAJOR=self._major, MINOR=self._minor, POWER=self._power, RSSI=self._rssi)


if __name__ == '__main__':
    # Create beacon service and scan for devices (2 seconds)
    service = BeaconService('hci0')
    devices = service.scan(2)
    # Connect to each beacon, print results of device scan
    for address, data in list(devices.items()):
        beacon = Beacon(address, data)
        print(beacon)
    print('*** Beacon scan complete! ***')