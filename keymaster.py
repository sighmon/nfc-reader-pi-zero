#######################################################
## Key Master - Hackerspace Adelaide NFC Door reader ##
#######################################################

# scard documentation:
# http://pyscard.sourceforge.net/epydoc/smartcard.scard.scard-module.html

# Post successful card scan to hackadl.org

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

import urllib
import urllib2
import base64
import sys
import argparse

from select import select
from smartcard.scard import *

import imp
try:
  imp.find_module('wiringpi2')
  hasWiringPi = True
except ImportError:
  hasWiringPi = False

if hasWiringPi:
  # For GPIO pin control
  import wiringpi2 as wiringpi  
  from time import sleep
  wiringpi.wiringPiSetupGpio()
  # Connect the pieso buzzer to GPIO 23
  # Ground to the third pin down from the top on the right column.
  # Power to the eighth pin down from the top on the right column.
  wiringpi.softToneCreate(23)

def hexarray(array):
  return ":".join(["{:02x}".format(b) for b in array])

def b64array(array):
  return base64.b64encode("".join([chr(b) for b in array]))

hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)

assert hresult==SCARD_S_SUCCESS

hresult, readers = SCardListReaders(hcontext, [])

assert len(readers)>0

reader = readers[0]
timeout = 10 # Timeout when there isn't any input
url = 'https://members.hackerspace-adelaide.org.au/'
devUrl = 'http://localhost:3000/'

# Parse arguments handed in when running

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--development", help="Run in development environment talking to localhost:3000.", action="store_true")
parser.add_argument("-l", "--lookup", help="Run in lookup mode, only for admins.", action="store_true")
app_args = parser.parse_args()

# Welcome message

print '\n###### Hackadl.org ######'
print '######  Oh hello.  ######\n'

# Welcome song

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
  print 'Development (d) or production (p)?'
  rlist, _, _ = select([sys.stdin], [], [], timeout)
  if rlist:
    answer = sys.stdin.readline()
    if answer[0] == 'd':
      url = devUrl
  else:
    print "No input. Defaulting to production."

if app_args.lookup:
  # Lookup mode
  url += 'lookup'
else:
  print 'Lookup (l) or checkin (c)?'
  rlist, _, _ = select([sys.stdin], [], [], timeout)
  if rlist:
    answer = sys.stdin.readline()
    if answer[0] == 'l':
      url += 'lookup'
    else:
      url += 'checkin'
  else:
    url += 'checkin'
    print "No input. Defaulting to checkin."

print 'URL: ' + url

## NFC reader code

readerstates = []
for i in xrange(len(readers)):
    readerstates += [ (readers[i], SCARD_STATE_UNAWARE) ]
hresult, newstates = SCardGetStatusChange(hcontext, 0, readerstates)

while True:
  hresult, newstates = SCardGetStatusChange(hcontext, 5000, newstates)
  for reader, eventstate, atr in newstates:
    if eventstate & SCARD_STATE_PRESENT:
      print 'Card found'
      hresult, hcard, dwActiveProtocol = SCardConnect(
      hcontext,
      reader,
      SCARD_SHARE_SHARED,
      SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)
      hresult, reader, state, protocol, atr = SCardStatus(hcard)
      print 'ATR:', hexarray(atr)
      hresult, response = SCardTransmit(hcard,dwActiveProtocol,[0xFF,0xCA,0x00,0x00,0x00])
      if response[-2:] == [0x90,0x00]:
        # Last two bytes 90 & 00 means success!
        # Remove them before printing the ID.
        id = response[:-2]
        print 'ID:', hexarray(id)
        # POST the card data
        try:
          data = urllib.urlencode({'atr' : b64array(atr), 'id' : b64array(response)})
          content = urllib2.urlopen(url, data).read()
          print content
          if hasWiringPi and content == "null":
            # Play bad sound
            wiringpi.softToneWrite(23, 2000)
            sleep(0.5)
            wiringpi.softToneWrite(23, 1000)
            sleep(0.5)
            wiringpi.softToneWrite(23, 0)
          else:
            # Play good sound
            for x in xrange(2000, 3000, 100):
              wiringpi.softToneWrite(23, x)
              sleep(0.05)
            for x in xrange(3000, 2000, -100):
              wiringpi.softToneWrite(23, x)
              sleep(0.05)
            wiringpi.softToneWrite(23, 0)
        except Exception, e:
          print e
          # Play bad sound
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
        print 'ID: error! Response: ', hexarray(response)
        print

    # elif eventstate & SCARD_STATE_EMPTY:
    	# Reader is empty, but commenting printing that to stop spamming on loop
    	# print 'Reader empty\n'

    # else:
      # Ignoring other event states too.
      # print 'Unknown event state', eventstate
