import asyncio
from pysnmp import debug
from pysnmp.hlapi.asyncio import *


''' Support class for interfacing with the PD-9624GC and PD-9612GC midspans of
    the techtile infrastructure.
'''
class midspan_support_class:

    __groupNr = 1                                           # fixed - don't change
    __portPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.3'		# POE-PRIVATE-MIB.portConsumptionPower
    __portMaxPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.4'     # POE-PRIVATE-MIB.portMaxPower

    ''' Constructor
        user        login for the SNMPv3 interface
        passKey     login passward for the SNMPv3 interface
    '''
    def __init__(self, user: str, passKey: str):
        self.__SNMPv3User = user
        self.__SNMPv3AuthKey = passKey
        self.__SNMPv3PrivKey = passKey
        #debug.set_logger(
        #    debug.Debug('io', 'msgproc', 'secmod', 'dsp', 'mibbuild')
        #)


    ''' Use SNMP to retrieve the status of a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number 
        returns     (onOff: int, portAction: str)
    '''
    def getPortStatus(self, midspanIP: str, portNr: int):
        (onOff, action) = asyncio.run(self.__getPortStatus(midspanIP, portNr))
        return (onOff, action)
        

    ''' Use SNMP to retrieve the power info about a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number
        returns     (power: int, maxPower: int, poeClass: str)
    '''
    def getPortPower(self, midspanIP: str, portNr: int):
        (power, maxPower, poeClass) = asyncio.run(self.__getPortPower(midspanIP, portNr))
        return (power, maxPower, poeClass)
    
    
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
        

    def __parse_poe_response(self, var_binds):
        columns = {
            3: "power_draw",
            4: "max_power"
        }

        data = {}

        for oid, value in var_binds:
            if value.__class__.__name__ == "NoSuchObject":
                continue

            oid_parts = str(oid).split(".")
            column = int(oid_parts[10])  # column position in this MIB

            if column in columns:
                data[columns[column]] = int(value)

        return (data.get("max_power"), data.get("power_draw"))


    ''' Use SNMP to retrieve the power info about a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number
        returns     (power: int, maxPower: int, poeClass: str)
        
        Don't use directly. Use getPortPower(...) instead.
    '''
    async def __getPortPower(self, midspanIP: str, portNr: str):
        engine = SnmpEngine()
        loginData = UsmUserData(
            self.__SNMPv3User,
            self.__SNMPv3AuthKey,
            self.__SNMPv3PrivKey,
            authProtocol=usmHMACMD5AuthProtocol,
            privProtocol=usmDESPrivProtocol
        )
        transport = await UdpTransportTarget.create((midspanIP, 161), timeout=5, retries=3)
        context = ContextData()

        # Build object types
        objs = [
            ObjectType(ObjectIdentity(self.__portMaxPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr))),
            ObjectType(ObjectIdentity(self.__portPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr)))
        ]

        # Perform SNMP GET asynchronously
        errorIndication, errorStatus, errorIndex, responses = await get_cmd(
            engine,
            loginData,
            transport,
            context,
            *objs
        )
        
        print("======== SNMP INFO =================")
        print(errorIndication)
        print(errorStatus)
        print(errorIndex)
        print(responses)

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
        
        Don't use directly. Use getPortStatus(...) instead.
    '''
    async def __getPortStatus(self, midspanIP: str, portNr: int):
        engine = SnmpEngine()
        loginData = UsmUserData(
            self.__SNMPv3User,
            self.__SNMPv3AuthKey,
            self.__SNMPv3PrivKey,
            authProtocol=usmHMACMD5AuthProtocol,
            privProtocol=usmDESPrivProtocol
        )
        transport = await UdpTransportTarget.create((midspanIP, 161), timeout=5, retries=3)
        context = ContextData()

        # Build object types
        objs = [
            ObjectType(ObjectIdentity(self.__portMaxPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr))),
            ObjectType(ObjectIdentity(self.__portPowerOID + '.' + str(self.__groupNr) + '.' + str(portNr)))
        ]

        # Perform SNMP GET asynchronously
        errorIndication, errorStatus, errorIndex, responses = await get_cmd(
            engine,
            loginData,
            transport,
            context,
            *objs
        )
        
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
                (max_power, power_draw) = self.__parse_poe_response(responses)
                
                if power_draw > 0:
                    onOff = 1
                else:
                    onOff = 0

        return (onOff, action)
    
    
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
