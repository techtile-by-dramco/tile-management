from pysnmp.hlapi import *
from pysnmp import debug

''' Support class for interfacing with the PD-9624GC and PD-9612GC midspans of
    the techtile infrastructure.
'''
class midspan_support_class:

    __groupNr = 1                                           # fixed - don't change
    __portPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.3'		# POE-PRIVATE-MIB.portConsumptionPower
    __portMaxPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.4'     # POE-PRIVATE-MIB.portmAXPower

    ''' Constructor
        user        login for the SNMPv3 interface
        passKey     login passward for the SNMPv3 interface
    '''
    def __init__(self, user: str, passKey: str):
        self.__SNMPv3LoginData = (user, passKey, passKey)
        debug.setLogger(debug.Debug('all'))


    ''' Use SNMP to retrieve the power info about a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number
        returns     (power: int, maxPower: int, poeClass: str)
    '''
    def getPortPower(self, midspanIp: str, portNr: int):
        loginData = self.__SNMPv3LoginData

        # build iterator for processing SNMP commands
        iterator = getCmd(
            SnmpEngine(),
            UsmUserData(*loginData),
            UdpTransportTarget((midspanIp, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(self.__portMaxPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr))),
            ObjectType(ObjectIdentity(self.__portPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr)))
        )

        # "run" the command
        errorIndication, errorStatus, errorIndex, responses = next(iterator)
        
        power = -1
        maxPower = -1
        poeClass = ''
        
        # parse the results
        if errorIndication:
            print(errorIndication)

        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and responses[int(errorIndex) - 1][0] or '?'))

        else: # we got a valid response
            if not len(responses) == 2:     # we only expect 2 responses (because we sent two commands)
                print('ERROR: unexpected response from midspan')
            else:
                # port maximum power (as integer) and power class
                try:
                    maxPower = int(responses[0][1].prettyPrint())
                    poeClass = 'class ' + str(self.__determineClass(maxPower))
                except ValueError:
                    maxPower = -1
                    poeClass = 'class unknown'
                
                # port power (as integer)
                try:
                    power = int(responses[1][1].prettyPrint())
                except ValueError:
                    power = -1
        
        return (power, maxPower, poeClass)


    ''' Use SNMP to retrieve the status of a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number 
        returns     (onOff: int, portAction: str)
    '''
    def getPortStatus(self, midspanIP: str, portNr: int):
        loginData = self.__SNMPv3LoginData

        # build iterator for processing SNMP commands
        iterator = getCmd(
            SnmpEngine(),
            UsmUserData(*loginData),
            UdpTransportTarget((midspanIP, 161)),
            ContextData(),
		    ObjectType(ObjectIdentity('POWER-ETHERNET-MIB', 'pethPsePortDetectionStatus', self.__groupNr, portNr)),
            ObjectType(ObjectIdentity('POWER-ETHERNET-MIB', 'pethPsePortAdminEnable', self.__groupNr, portNr)),
        )

        # "run" the command
        errorIndication, errorStatus, errorIndex, responses = next(iterator)

        onOff = -1
        action = "SNMP Error"

        # parse the results
        if errorIndication:
            print(errorIndication)

        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and responses[int(errorIndex) - 1][0] or '?'))

        else: # we got a valid response
            if not len(responses) == 2:     # we only expect 2 responses (because we sent two commands)
                print('ERROR: unexpected response from midspan')
            else:
                # port action
                action = responses[0][1].prettyPrint()
                
                # port on/off
                if responses[1][1].prettyPrint() == 'true':
                    onOff = 1
                else:
                    onOff = 0

        return (onOff, action)


    ''' Use SNMP to enable or disable specific port on a midspan
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number 
        returns     result of the action
    '''
    def setPortOnOff(self, midspanIP: str, portNr: int, onOff: int):
        if onOff == 1:
            return self.__setPortOnOff(midspanIP, portNr, 'true')
        elif onOff == 0:
            return self.__setPortOnOff(midspanIP, portNr, 'false')
        else:
            return -1


    ''' For internal use only
        onOff argument is passed as either 'true' or 'false'
    '''
    def __setPortOnOff(self, midspanIP: str, portNr: int, onOff: str):
        loginData = self.__SNMPv3LoginData

        # build iterator for processing SNMP commands
        iterator = setCmd(
            SnmpEngine(),
            UsmUserData(*loginData),
            UdpTransportTarget((midspanIP, 161)),
            ContextData(),
            ObjectType(ObjectIdentity('POWER-ETHERNET-MIB', 'pethPsePortAdminEnable', self.__groupNr, portNr), onOff),
        )

        errorIndication, errorStatus, errorIndex, responses = next(iterator)

        if errorIndication:
            print(errorIndication)
            return -1
            
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and responses[int(errorIndex) - 1][0] or '?'))
            return -1

        else:   # we got a valid response
            if not len(responses) == 1:     # we only expect 1 response (because we sent two commands)
                print('ERROR: unexpected response from midspan')
            else:
                # port on/off
                if responses[0][1].prettyPrint() == 'true':
                    return 1
                else:
                    return 0

        
    ''' Basic mapping from a max. power rating to a PoE class
        power       maximum power reserved by the port determines the PoE class
        returns     poeClass: int (between 1 and 8)
    '''
    def __determineClass(self, power: int):
        if power < 6:
            return 1
        if power < 10:
            return 2
        if power < 20:
            return 3
        if power < 35:
            return 4
        if power < 50:
            return 5
        if power < 65:
            return 6
        if power < 80:
            return 7        
        return 8	
