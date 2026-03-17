import asyncio
from pysnmp import debug
from pysnmp.hlapi.asyncio import *
from pathlib import Path
import yaml


''' Support class for interfacing with the PD-9624GC and PD-9612GC midspans of
    the techtile infrastructure.
    Based on Microsemi Tech Note 132 "Using RFC3621 PoE MIB With Microsemi Midspans"
'''
class midspan_support_class:
    __groupNr = 1                                               # fixed - don't change
    __pethPsePortAdminEnableOID = '.1.3.6.1.2.1.105.1.1.1.3'    # POWER-ETHERNET-MIB.pethPsePortAdminEnable
    __portPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.3'		    # POE-PRIVATE-MIB.portConsumptionPower
    __portMaxPowerOID = '.1.3.6.1.4.1.7428.1.2.1.1.1.4'         # POE-PRIVATE-MIB.portMaxPower
    __ON = 1
    __OFF = 2

    ON = 1
    OFF = 0
    
    ''' Constructor
        user        login for the SNMPv3 interface
        passKey     login passward for the SNMPv3 interface
    '''
    def __init__(self, user: str, passKey: str):
        self.__SNMPv3User = user
        self.__SNMPv3AuthKey = passKey
        self.__SNMPv3PrivKey = passKey
        
        baseDir = Path(__file__).resolve().parent.parent
        inventoryFile = baseDir / "inventory/hosts.yaml"    
        with open(inventoryFile) as f:
            self.__inventory = yaml.safe_load(f)

        self.__sem = asyncio.Semaphore(8)

    ''' Use SNMP to retrieve the status of a specific midspan port
        midspanIP   midspan ip address (e.g. '192.168.1.2')
        portNr      port number 
        returns     (onOff: int, portPower: int, portMaxPower: int, poeClass: int)
    '''
    def getPortStatus(self, host: str):
        (midspanIP, portNr) = self.__get_poe_info(host)
        (onOff, portPower, portMaxPower, poeClass) = asyncio.run(self.__getPortStatus(midspanIP, portNr))
        return (onOff, portPower, portMaxPower, poeClass)
    
    
    ''' Use SNMP to enable or disable specific port on a midspan
        host        (list of) hostname(s) to turn on or off.
                    These should correspond with the hosts defined in inventory/hosts.yaml
        onOff       midspan_support_class.ON or midspan_support_class.OFF
        returns     result of the action
    '''
    def setPortOnOff(self, host: str | list[str], onOff: int):
        if isinstance(host, str):
            host = [host]  # wrap single string in a list
            
        print(host)
        results = asyncio.run(self.__setPortOnOffAsync(host, onOff))
        return results
    

    async def __setPortOnOffAsync(self, host: list[str], onOff: int):
        tasks = []
        for h in host:
            (midspanIP, portNr) = self.__get_poe_info(h)
            if onOff == midspan_support_class.ON:
                tasks.append(self.__safeSetPortOnOff(midspanIP, portNr, midspan_support_class.__ON))
            if onOff == midspan_support_class.OFF:
                tasks.append(self.__safeSetPortOnOff(midspanIP, portNr, midspan_support_class.__OFF))
            else:
                return -1
        
        print(tasks)
        results = await asyncio.gather(*tasks)
        return results
    

    async def __safeSetPortOnOff(self, midspanIP, portNr, onOff: int):
        async with midspan_support_class.__sem: # don't use self.__sem!
            return await self.__setPortOnOff(midspanIP, portNr, onOff)


    def __parse_poe_response(self, var_binds):
        columns = {
            3: "powerDraw",
            4: "maxPower"
        }

        data = {}

        for oid, value in var_binds:
            if value.__class__.__name__ == "NoSuchObject":
                continue

            oid_parts = str(oid).split(".")
            column = int(oid_parts[12])  # column position in this MIB

            if column in columns:
                data[columns[column]] = int(value)

        return (data.get("maxPower"), data.get("powerDraw"))


    def __get_poe_info(self, host):
        hosts = self.__inventory["all"]["hosts"]
        midspans = self.__inventory["all"]["vars"]["midspans"]

        if host not in hosts:
            raise ValueError(f"Host {host} not found")

        host_data = hosts[host]

        poe_port = host_data.get("poe-port")
        midspan = host_data.get("midspan")

        if not midspan:
            return None

        midspan_ip = midspans[midspan]["ip"]

        return (midspan_ip, poe_port)


    ''' Use SNMP to retrieve the status of a specific midspan port
        
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
            ObjectType(ObjectIdentity(midspan_support_class.__portMaxPowerOID + '.' + str(midspan_support_class.__groupNr) + '.' + str(portNr))),
            ObjectType(ObjectIdentity(midspan_support_class.__portPowerOID + '.' + str(midspan_support_class.__groupNr) + '.' + str(portNr)))
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
        powerDraw = -1
        maxPower = -1

        # parse the results
        if errorIndication:
            print(errorIndication)

        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and responses[int(errorIndex) - 1][0] or '?'))

        else: # we got a valid response
            if not len(responses) == 2:     # we only expect 2 responses (because we've sent 2 commands)
                print('ERROR: unexpected response from midspan')
            else:
                (maxPower, powerDraw) = self.__parse_poe_response(responses)
                
                if powerDraw > 0:
                    onOff = 1
                else:
                    onOff = 0

        return (onOff, powerDraw, maxPower, self.__determineClass(maxPower))
    
    
    ''' For internal use only
        onOff argument is passed as either 'true' or 'false'
    '''
    async def __setPortOnOff(self, midspanIP: str, portNr: int, onOff: int):
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
            ObjectType(ObjectIdentity(midspan_support_class.__pethPsePortAdminEnableOID + '.' + str(midspan_support_class.__groupNr) + '.' + str(portNr)), Integer(onOff))
        ]

        # Perform SNMP SET asynchronously
        errorIndication, errorStatus, errorIndex, responses = await set_cmd(
            engine,
            loginData,
            transport,
            context,
            *objs
        )

        if errorIndication:
            print(errorIndication)
            return -1
            
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and responses[int(errorIndex) - 1][0] or '?'))
            return -1

        else:   # we got a valid response
            if not len(responses) == 1:     # we only expect 1 response (because we've sent 1 command)
                print('ERROR: unexpected response from midspan')
            else:
                # port on/off
                if responses[0][1].prettyPrint() == 'true':
                    return 1
                else:
                    return 0

        
    ''' Basic mapping from a max. power rating to a PoE class
        power       maximum power reserved by the port determines the PoE class
        returns     poeClass: int (between 1 and 8) or -1 when power is 0
    '''
    def __determineClass(self, power: int):
        if power == 0:
            return -1
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
