#!/usr/bin/env python3

"""
This is a NodeServer for Nanoleaf written by automationgeek (Jean-Francois Tremblay) 
based on the NodeServer template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com.
Using this Python Library to control NanoLeaf by Software2 https://github.com/software-2/nanoleaf
"""

import polyinterface
import time
import json
import sys
from nanoleaf import setup
from nanoleaf import Aurora

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

# EFFECT = ['', 'Flames', 'Forest', 'Nemo', 'Northern Lights', 'Romantic', 'Snowfall', 'Fireworks and Firecrackers']

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'NanoLeaf'
        self.initialized = False
        self.tries = 0
        self.nano_ip = None
        self.nano_token = None
        self.requestNewToken = 0
        
    def start(self):
        LOGGER.info('Started NanoLeaf for v2 NodeServer version %s', str(VERSION))
        try:
            custom_data_ip = False
            custom_data_token = False
            
            if 'requestNewToken' in self.polyConfig['customParams']:
                self.requestNewToken = self.polyConfig['customParams']['requestNewToken']    
            
            if self.requestNewToken == 1:
                if 'ip' in self.polyConfig['customParams'] and self.nano_ip is None:
                    self.nano_ip = self.polyConfig['customParams']['ip']
                    LOGGER.info('Custom IP address specified: {}'.format(self.nano_ip))
                if 'token' in self.polyConfig['customParams'] and self.nano_token is None:
                    self.nano_token = self.polyConfig['customParams']['token']
                    LOGGER.info('Custom Token specified: {}'.format(self.nano_token))
            else:
                if 'customData' in self.polyConfig:
                    if 'nano_ip' in self.polyConfig['customData']:
                        self.nano_ip = self.polyConfig['customData']['nano_ip']
                        custom_data_ip = True
                        LOGGER.info('Nano IP found in the Database: {}'.format(self.nano_ip))
                    if 'nano_token' in self.polyConfig['customData']:
                        self.nano_token = self.polyConfig['customData']['nano_token']
                        custom_data_token = True
                        LOGGER.info('Nano token found in the Database.')
                else:
                    LOGGER.cinfo('Custom Data is not found in the DB')
       
            if self.nano_ip is None:
                LOGGER.error('Need to have ip address in custom param ip')
                self.setDriver('ST', 0)
                return False
            
            # Obtain NanoLeaf token, make sure to push on the power button of Aurora until Light is Flashing
            if self.nano_token is None:
                LOGGER.debug('Requesting Token')
                self.nano_token = setup.generate_auth_token(self.nano_ip)
                LOGGER.debug(self.nano_token)
                if self.nano_token is None:
                    LOGGER.error('Unable to obtain the token, make sure the NanoLeaf is in Linking mode')
                    self.setDriver('ST', 0)
                    return False      
            
            if custom_data_ip == False or custom_data_token == False:
                LOGGER.debug('Saving access credentials to the Database')
                data = { 'nano_ip': self.nano_ip, 'nano_token': self.nano_token }
                self.saveCustomData(data)
            
            self.setDriver('ST', 1)
            self.discover()
                                                            
        except Exception as ex:
            LOGGER.error('Error starting NanoLeaf NodeServer: %s', str(ex))
            self.setDriver('ST', 0)
            return False

    def shortPoll(self):
        pass

    def longPoll(self):
        self.query()

    def query(self):
        self.reportDrivers()
        for node in self.nodes:
            if self.nodes[node].address != self.address and self.nodes[node].do_poll:
                self.nodes[node].query()

    def discover(self, *args, **kwargs):
        time.sleep(1)
        self.addNode(AuroraNode(self, self.address, 'myaurora', 'MyAurora'))

    def delete(self):
        LOGGER.info('Deleting NanoLeaf')
        
    id = 'controller'
    commands = {}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
class AuroraNode(polyinterface.Node):

    def __init__(self, controller, primary, address, name):
        self.do_poll = True
        self.timeout = 5.0
        self.arrEffects = None
     
        super(AuroraNode, self).__init__(controller, primary, address, name)
        self.my_aurora = Aurora(self.parent.nano_ip,self.parent.nano_token)
        self._getEffetsList()
        self.query()

    def start(self):
        self.query()                                          
        
    def setOn(self, command):
        self.my_aurora.on = True
        self.setDriver('ST', 100)

    def setOff(self, command):
        self.my_aurora.on = False
        self.setDriver('ST', 0)
        
    def setBrightness(self, command):
        intBri = int(command.get('value'))
        self.my_aurora.brightness =   intBri                                                   
        self.setDriver('GV3', intBri)

    def setEffect(self, command):
        intEffect = int(command.get('value'))
        LOGGER.info(self.arrEffects)
        self.my_aurora.effect = self.arrEffects[intEffect+1]
        self.setDriver('GV4', intEffect)
      
    def query(self):
        self._updateValue()
        self.reportDrivers()

    def _updateValue(self):
        if self.my_aurora.on is True:
            self.setDriver('ST', 100)
        else:
            self.setDriver('ST', 0)
        self.setDriver('GV3', self.my_aurora.brightness )
        self.setDriver('GV4', EFFECT.index(self.my_aurora.effect))
    
    def _saveEffetsList(self)
        self.arrEffects = self.my_aurora.effects_list
        
        #Write effectLists to Json
        try:
            with open("effectLists.json", "w") as outfile:
                json.dump(arrEffects, outfile)
        except IOError:
            LOGGER.error('Unable to write effectLists.json')
                
    def _getEffetsList(self)
        try:
            with open("effectLists.json", "r") as infile:
                self.arrEffects = json.load(infile)
         except IOError:
            _saveEffetsList(self)
        
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 78},
               {'driver': 'GV3', 'value': 0, 'uom': 51},
               {'driver': 'GV4', 'value': 1, 'uom': 25}]
    id = 'AURORA'
    commands = {
                    'DON': setOn,
                    'DOF': setOff,
                    'SET_BRI': setBrightness,
                    'SET_EFFECT': setEffect
                }
    
if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('NanoLeafNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
