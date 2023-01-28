#!/usr/bin/env python3

"""
This is a NodeServer for Nanoleaf Aurora written by automationgeek (Jean-Francois Tremblay) 
based on the NodeServer template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com.
Using this Python Library to control NanoLeaf by https://github.com/Oro/pynanoleaf
"""

import udi_interface
import time
import json
import sys
import os
import zipfile
from copy import deepcopy
from threading import Thread
from pynanoleaf import Nanoleaf, Unavailable

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

def get_profile_info(logger):
    pvf = 'profile/version.txt'
    try:
        with open(pvf) as f:
            pv = f.read().replace('\n', '')
    except Exception as err:
        logger.error('get_profile_info: failed to read  file {0}: {1}'.format(pvf,err), exc_info=True)
        pv = 0
    f.close()
    return { 'version': pv }

class Controller(udi_interface.Node):

    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.name = 'NanoLeaf'
        self.hb = 0
        self.queryON = False
        self.nano_ip = None
        self.nano_token = None
        self.discovery_thread = None

        self.CustomData = Custom(polyglot, 'customdata')

        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.CUSTOMDATA, self.customDataHandler)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.POLL, self.poll)

        polyglot.ready()
        polyglot.addNode(self)
        
    def customDataHandler(self, data):
        self.CustomData.load(data)

    def parameterHandler(self, params):
        self.poly.Notices.clear()

        # Get and set IP
        if 'ip' in params and params['ip'] != "":
            self.nano_ip = params['ip']
            LOGGER.info('Custom IP address specified: {}'.format(self.nano_ip))
        else:
            LOGGER.error('Need to have ip address in custom param ip')
            self.setDriver('ST', 0, True)
            return False
          
        # Get saved token
        if 'nano_token' in self.CustomData:
            self.nano_token = self.CustomData['nano_token']
            if self.nano_token  == ' ' :
                self.nano_token = None
            LOGGER.debug('Retrieved token : {}'.format(self.nano_token))
            
        # If token is provided overwrite the saved token
        if 'token' in params:
            self.nano_token = params['token']
            self.CustomData['nano_token'] = self.nano_token
            LOGGER.debug('Custom token specified: {}'.format(self.nano_token))
            LOGGER.info('Saving token to the Database')
            
        # Reinitialize token only if token was not provided
        if 'requestNewToken' in params and 'token' not in params :
            self.nano_token = None
            self.CustomData['nano_token'] = ' '
            LOGGER.debug('Resetting token')
                
        # Obtain NanoLeaf token, make sure to push on the power button of Aurora until Light is Flashing
        if self.nano_token is None :
            LOGGER.debug('Requesting Token')
            for myHost in self.nano_ip.split(','):
                nanoleaf = Nanoleaf(host=myHost)
                myToken = nanoleaf.request_token()
                if myToken is None:
                    myToken = ' '
                    LOGGER.error('Unable to obtain one of the token, make sure all NanoLeaf are in Linking mode.')
                       
                if self.nano_token is None:
                    self.nano_token = myToken
                else:
                    self.nano_token = self.nano_token + ',' + myToken
          
            self.CustomData['nano_token'] = self.nano_token
            LOGGER.debug('Token received: {}'.format(self.nano_token))
            LOGGER.info('Saving token to the Database')

        self.discover()

    def start(self):
        LOGGER.info('Started NanoLeaf Aurora for v3 NodeServer version %s', str(VERSION))
        try:
            self.setDriver('ST', 1)
            self.poly.updateProfile()
            self.poly.setCustomParamsDoc()
        except Exception as ex:
            LOGGER.error('Error starting NanoLeaf NodeServer: %s', str(ex))
            self.setDriver('ST', 0)
            return False

    def poll(self, polltype):
        if 'shortPoll' in polltype:
            if self.discovery_thread is not None:
                if self.discovery_thread.is_alive():
                    LOGGER.debug('Skipping shortPoll() while discovery in progress...')
                    return
                else:
                    self.discovery_thread = None
        
            for node in self.poly.nodes():
                if node.queryON == True :
                    node.update()
        else:
            self.heartbeat()

    def query(self):
        for node in self.poly.nodes():
            node.reportDrivers() 
        
    def heartbeat(self):
        LOGGER.debug('heartbeat hb={}'.format(str(self.hb)))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0
        
    def install_profile(self):
        try:
            self.poly.updateProfile()
            LOGGER.info('Please restart the Admin Console for change to take effect')
        except Exception as ex:
            LOGGER.error('Error installing profile: %s', str(ex))
        return True
   
    def runDiscover(self,command):
        self.discover()
    
    def discover(self, *args, **kwargs):  
        if self.discovery_thread is not None:
            if self.discovery_thread.is_alive():
                LOGGER.info('Discovery is still in progress')
                return
        self.discovery_thread = Thread(target=self._discovery_process)
        self.discovery_thread.start()

    def _discovery_process(self):
        lstIp = self.nano_ip.split(',')
        lstToken = self.nano_token.split(',')
        lstAccess = None
        
        if ( len(lstIp) == len(lstToken) ):
            id = 1 
            lstAccess = list(zip(lstIp, lstToken))
            for access in lstAccess:
                self.poly.addNode(AuroraNode(self.poly, self.address, 'aurora' + str(id) , 'Aurora' + str(id), access[0], access[1]))
                id = id + 1 
        else:
            LOGGER.error('Unable to initialize the AuroraNode, list of host and token does not match.')
        
    def delete(self):
        LOGGER.info('Deleting NanoLeaf')
        
    id = 'controller'
    commands = {'DISCOVERY' : runDiscover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
class AuroraNode(udi_interface.Node):

    def __init__(self, controller, primary, address, name, ip, token):
        super(AuroraNode, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.nano_ip = ip
        self.nano_token = token
        self.arrEffects = None
        self.parent = controller.getNode(primary)
        
        try:
            self.my_aurora = Nanoleaf(host=self.nano_ip,token=self.nano_token)
        except Exception as ex:
            LOGGER.error('Error unable to connect to NanoLeaf Aurora: %s', str(ex))
            
        self.__getEffetsList()
        self.__BuildProfile()
        self.query()

    def setOn(self, command):
        try:
            self.my_aurora.on = True
            self.setDriver('ST', 100)
        except:
            pass

    def setOff(self, command):
        try:
            self.my_aurora.off = True
            self.setDriver('ST', 0)
        except:
            pass
        
    def setBrightness(self, command):
        try:
            intBri = int(command.get('value'))
            self.my_aurora.brightness = intBri                                                   
            self.setDriver('GV3', intBri)
        except:
            pass

    def setEffect(self, command):
        try:
            intEffect = int(command.get('value'))
            self.my_aurora.effect = self.arrEffects[intEffect-1]
            self.setDriver('GV4', intEffect)
        except:
            pass
    
    def setProfile(self, command):
        self.__saveEffetsList()
        self.__BuildProfile()
    
    def query(self):
        self.reportDrivers()

    def update(self):
        try:
            if self.my_aurora.on is True:
                self.setDriver('ST', 100)
            else:
                self.setDriver('ST', 0)
            self.setDriver('GV3', self.my_aurora.brightness)
            self.setDriver('GV4', self.arrEffects.index(self.my_aurora.effect)+1)
        except Exception as ex:
            LOGGER.error('Error updating Aurora value: %s', str(ex))
    
    def __saveEffetsList(self):
        try:
            self.arrEffects = self.my_aurora.effects
        except Exception as ex:
            LOGGER.error('Unable to get NanoLeaf Effet List: %s', str(ex))
            
        #Write effectLists to Json
        try:
            with open(".effectLists.json", "w+") as outfile:
                json.dump(self.arrEffects, outfile)
        except IOError:
            LOGGER.error('Unable to write effectLists.json')
              
    def __getEffetsList(self):
        try:
            with open(".effectLists.json", "r") as infile:
                self.arrEffects = json.load(infile)
        except IOError:
            self.__saveEffetsList()
    
    def __BuildProfile(self):
        try:
            # Build File NLS from Template
            with open("profile/nls/en_us.template") as f:
                with open("profile/nls/en_us.txt", "w+") as f1:
                    for line in f:
                        f1.write(line) 
                    f1.write("\n") 
                f1.close()
            f.close()

            # Add Effect to NLS Profile        
            with open("profile/nls/en_us.txt", "a") as myfile:
                intCounter = 1
                for x in self.arrEffects:  
                    myfile.write("EFFECT_SEL-" + str(intCounter) + " = " + x + "\n")
                    intCounter = intCounter + 1
            myfile.close()

            intArrSize = len(self.arrEffects)
            if intArrSize is None or intArrSize == 0 :
                intArrSize = 1

            with open("profile/editor/editors.template") as f:
                with open("profile/editor/editors.xml", "w+") as f1:
                    for line in f:
                        f1.write(line) 
                    f1.write("\n") 
                f1.close()
            f.close()

            with open("profile/editor/editors.xml", "a") as myfile:
                myfile.write("\t<editor id=\"MEFFECT\">"  + "\n")
                myfile.write("\t\t<range uom=\"25\" subset=\"1-"+ str(intArrSize) + "\" nls=\"EFFECT_SEL\" />"  + "\n")
                myfile.write("\t</editor>" + "\n")
                myfile.write("</editors>")
            myfile.close()
        
        except Exception as ex:
            LOGGER.error('Error generating profile: %s', str(ex))
        
        self.parent.install_profile()

        
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 78},
               {'driver': 'GV3', 'value': 0, 'uom': 51},
               {'driver': 'GV4', 'value': 1, 'uom': 25}]
    
    id = 'AURORA'
    commands = {
                    'QUERY': query,            
                    'DON': setOn,
                    'DOF': setOff,
                    'SET_PROFILE' : setProfile,
                    'SET_BRI': setBrightness,
                    'SET_EFFECT': setEffect
                }
    
if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start()
        Controller(polyglot, 'controller', 'controller', 'NanoLeafNodeServer')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
