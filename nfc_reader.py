################################################
## NFC Reader - MuseumOS NFC prototype reader ##
################################################

# scard documentation:
# http://pyscard.sourceforge.net/epydoc/smartcard.scard.scard-module.html

# Post successful card scan to museumos-prod.acmi.net.au

# When running on a Raspberri Pi, you need to install these:
# $ sudo apt-get install python-pyscard
# $ sudo apt-get install pcscd
# $ sudo apt-get install pcsc-tools

# If the reader isn't showing up, solve it using this:
# http://enjoy-rfid.blogspot.com.au/2015/03/raspberry-pi-nfc.html
# Which gets you to create a blacklist file:
# /etc/modprobe.d/raspi-blacklist.conf 
# That just has:
# blacklist pn533
# blacklist nfc

# For a hacky way to make this run at boot on the RaspberryPi,
# running this from /etc/rc.local

import urllib.request
import base64
import sys
import argparse
import syslog
import os
import socket
import config
import json
import pytz
import hashlib
import uuid
import imp

from select import select
from smartcard.scard import *

from datetime import datetime

from threading import Thread
import time

# Tag logs to syslog with nfc_reader
syslog.openlog('nfc_reader')

# Shutdown card ATR & ID
shutdownATR = config.adminCardATR
shutdownID = config.adminCardUID

# MD5 secret
md5secret = config.md5secret

# Set pytz timezone
pytz_timezone = pytz.timezone('Australia/Melbourne')

# Get mac address
def get_mac():
  mac_num = hex(uuid.getnode()).replace('0x', '').upper()
  mac = ':'.join(mac_num[i : i + 2] for i in range(0, 11, 2))
  return mac

# Get IP address
def get_ip_address():
  return (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]
ip_address = get_ip_address()
reader_name = 'nfc-' + ip_address.split('.')[-1]

def datetimeNowTimeZoneIso8601():
  return datetime.now(pytz_timezone).isoformat()

def generateMD5ForTap():
  m = hashlib.md5()
  currentDateTime = datetime.now(pytz_timezone)
  datetimeMD5Format = currentDateTime.strftime("%Y/%m/%d-%H:%M:%S")
  m.update((md5secret + datetimeMD5Format).encode('utf-8'))
  return m.hexdigest()

try:
  imp.find_module('wiringpi')
  hasWiringPi = True
except ImportError:
  hasWiringPi = False

if hasWiringPi:
  # For GPIO pin control
  import wiringpi as wiringpi  
  from time import sleep
  wiringpi.wiringPiSetupGpio()
  # Connect the pieso buzzer to GPIO 23
  # Ground to the third pin down from the top on the right column.
  # Power to the eighth pin down from the top on the right column.
  wiringpi.softToneCreate(23)

def hexarray(array):
  return "".join(["{:02x}".format(b) for b in array])

def b64array(array):
  return base64.b64encode("".join([chr(b) for b in array]))

def printToScreenAndSyslog(*args):
  print(" ".join(args))
  syslog.syslog(" ".join(args))

hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)

assert hresult==SCARD_S_SUCCESS

hresult, readers = SCardListReaders(hcontext, [])

assert len(readers)>0

reader = readers[0]
timeout = 10 # Timeout when there isn't any input
url = config.prodUrl
devUrl = config.devUrl
heartbeatFrequency = config.heartbeatFrequency
readerModel = config.readerModel

# Parse arguments handed in when running

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--development", help="Run in development environment talking to localhost:3000.", action="store_true")
parser.add_argument("-l", "--lookup", help="Run in lookup mode, only for admins.", action="store_true")
app_args = parser.parse_args()

# Welcome message

printToScreenAndSyslog('\n###### MuseumOS ######')
printToScreenAndSyslog('######  Oh hello.  ######\n')

# Welcome song

if hasWiringPi:
  wiringpi.softToneWrite(23, 1000)
  sleep(0.05)
  wiringpi.softToneWrite(23, 0)
  sleep(0.05)
  wiringpi.softToneWrite(23, 1000)
  sleep(0.05)
  wiringpi.softToneWrite(23, 0)
  sleep(0.05)
  wiringpi.softToneWrite(23, 1000)
  sleep(0.05)
  wiringpi.softToneWrite(23, 0)
  sleep(0.05)
  wiringpi.softToneWrite(23, 1500)
  sleep(0.5)
  wiringpi.softToneWrite(23, 0)

if app_args.development:
  # Development mode
  url = devUrl
else:
  printToScreenAndSyslog('Development (d) or production (p)?')
  rlist, _, _ = select([sys.stdin], [], [], timeout)
  if rlist:
    answer = sys.stdin.readline()
    if answer[0] == 'd':
      url = devUrl
  else:
    printToScreenAndSyslog("No input. Defaulting to production.")

taps_api = url + '/api/taps/'
statuses_api = url + '/api/statuses/'
printToScreenAndSyslog('MuseumOS: ' + url)
printToScreenAndSyslog('Taps endpoint: ' + taps_api)
printToScreenAndSyslog('Statuses endpoint: ' + statuses_api)

# Send heartbeat in a background thread
def heartbeat():
    while not heartbeat.cancelled:
        try:
          data = {
            'nfc_reader': {
              'mac_address': get_mac(),
              'reader_ip': ip_address,
              'reader_name': reader_name,
              'reader_model': readerModel
            },
            'status_datetime': datetimeNowTimeZoneIso8601()  # ISO8601 format
          }
          printToScreenAndSyslog('Heartbeat: ' + json.dumps(data))
          request = urllib.request.Request(statuses_api)
          request.add_header('Content-Type', 'application/json; charset=utf-8')
          jsonData = json.dumps(data)
          jsonDataBytes = jsonData.encode('utf-8')
          request.add_header('Content-Length', len(jsonDataBytes))
          content = urllib.request.urlopen(request, jsonDataBytes).read()
        except Exception as e:
          printToScreenAndSyslog('Exception: ', str(e))
        time.sleep(heartbeatFrequency)
heartbeat.cancelled = False

thread = Thread(target=heartbeat)
thread.start()

## NFC reader code

readerstates = []
for i in range(len(readers)):
    readerstates += [ (readers[i], SCARD_STATE_UNAWARE) ]
hresult, newstates = SCardGetStatusChange(hcontext, 0, readerstates)

while True:
  try:
    hresult, newstates = SCardGetStatusChange(hcontext, 5000, newstates)
    for reader, eventstate, atr in newstates:
      if eventstate & SCARD_STATE_PRESENT:
        printToScreenAndSyslog('Card found')
        hresult, hcard, dwActiveProtocol = SCardConnect(
        hcontext,
        reader,
        SCARD_SHARE_SHARED,
        SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)

        # Turn off buzzer
        hresult, response = SCardTransmit(hcard,dwActiveProtocol,[0xFF,0x00,0x52,0x00,0x00])
        if response[-2:] == [0x90,0x00]:
          printToScreenAndSyslog("successfully turned off buzzer.")

        hresult, reader, state, protocol, atr = SCardStatus(hcard)
        printToScreenAndSyslog('ATR:', hexarray(atr))
        hresult, response = SCardTransmit(hcard,dwActiveProtocol,[0xFF,0xCA,0x00,0x00,0x00])
        if response[-2:] == [0x90,0x00]:
          # Last two bytes 90 & 00 means success!
          # Remove them before printing the ID.
          id = response[:-2]
          printToScreenAndSyslog('ID:', hexarray(id))
          # POST the card data
          try:
            data = {
              'nfc_tag': {
                'atr': hexarray(atr),
                'uid': hexarray(id)
              },
              'nfc_reader': {
                'mac_address': get_mac(),
                'reader_ip': ip_address,
                'reader_name': reader_name,
                'reader_model': readerModel,
              },
              'tap_datetime': datetimeNowTimeZoneIso8601(),  # ISO8601 format
              'md5': generateMD5ForTap()
            }
            printToScreenAndSyslog(json.dumps(data))
            request = urllib.request.Request(taps_api)
            request.add_header('Content-Type', 'application/json; charset=utf-8')
            jsonData = json.dumps(data)
            jsonDataBytes = jsonData.encode('utf-8')
            request.add_header('Content-Length', len(jsonDataBytes))
            content = urllib.request.urlopen(request, jsonDataBytes).read()
            printToScreenAndSyslog(content.decode('utf-8'))
            if hexarray(atr) == shutdownATR and hexarray(id) == shutdownID:
              # Shutdown card
              if hasWiringPi:
                wiringpi.softToneWrite(23, 2000)
                sleep(0.5)
                wiringpi.softToneWrite(23, 1000)
                sleep(0.5)
                wiringpi.softToneWrite(23, 750)
                sleep(0.5)
                wiringpi.softToneWrite(23, 250)
                sleep(0.5)
                wiringpi.softToneWrite(23, 0)
              # shutdown
              os.system('shutdown now')
            elif hasWiringPi and content == "null":
              # Play bad sound
              if hasWiringPi:
                wiringpi.softToneWrite(23, 2000)
                sleep(0.5)
                wiringpi.softToneWrite(23, 1000)
                sleep(0.5)
                wiringpi.softToneWrite(23, 0)
            else:
              # Play good sound
              if hasWiringPi:
                for x in range(2000, 3000, 100):
                  wiringpi.softToneWrite(23, x)
                  sleep(0.05)
                for x in range(3000, 2000, -100):
                  wiringpi.softToneWrite(23, x)
                  sleep(0.05)
                wiringpi.softToneWrite(23, 0)
          except Exception as e:
            printToScreenAndSyslog('Exception: ', str(e))
            # Play bad sound
            if hasWiringPi:
              wiringpi.softToneWrite(23, 2000)
              sleep(0.5)
              wiringpi.softToneWrite(23, 1000)
              sleep(0.5)
              wiringpi.softToneWrite(23, 750)
              sleep(0.5)
              wiringpi.softToneWrite(23, 0)
          else:
            pass
        else:
          # Unsuccessful read.
          printToScreenAndSyslog('ID: error! Response: ', hexarray(response))
          # printToScreenAndSyslog()
      # elif eventstate & SCARD_STATE_EMPTY:
        # Reader is empty, but commenting printing that to stop spamming on loop
        # print 'Reader empty\n'

      # else:
        # Ignoring other event states too.
        # print 'Unknown event state', eventstate
  except KeyboardInterrupt as e:
    printToScreenAndSyslog('Closing, so cancel heartbeat.')
    heartbeat.cancelled = True
    # TODO: Fix exiting...
    # thread.interrupt_main()
    os._exit
    os.kill()
