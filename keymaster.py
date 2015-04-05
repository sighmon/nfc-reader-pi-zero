#######################################################
## Key Master - Hackerspace Adelaide NFC Door reader ##
#######################################################

# scard documentation:
# http://pyscard.sourceforge.net/epydoc/smartcard.scard.scard-module.html

# TODO: Post successful card scan to hackadl.org

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

import urllib
import urllib2
import base64

from smartcard.scard import *

def hexarray(array):
  return ":".join(["{:02x}".format(b) for b in array])

def b64array(array):
  return base64.b64encode("".join([chr(b) for b in array]))

hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)

assert hresult==SCARD_S_SUCCESS

hresult, readers = SCardListReaders(hcontext, [])

assert len(readers)>0

reader = readers[0]

print '\n###### Hackadl.org ######'
print '######  Oh hello.  ######\n'

print 'Development (d) or production (p)?'
answer = raw_input()

if answer == 'd':
  url = 'http://localhost:3000/'
else:
  url = 'http://members.hackadl.org/'

print 'Lookup (l) or checkin (c)?'
answer = raw_input()

if answer == 'l':
  url += 'lookup'
else:
  url += 'checkin'

print 'URL: ' + url

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
        data = urllib.urlencode({'atr' : b64array(atr), 'id' : b64array(response)})
        content = urllib2.urlopen(url, data).read()
        print content
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
