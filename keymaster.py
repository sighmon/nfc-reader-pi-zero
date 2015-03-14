#######################################################
## Key Master - Hackerspace Adelaide NFC Door reader ##
#######################################################

# scard documentation:
# http://pyscard.sourceforge.net/epydoc/smartcard.scard.scard-module.html

# TODO: Post successful card scan to hackadl.org

import urllib
import urllib2

from smartcard.scard import *

def hexarray(array):
  return ":".join(["{:02x}".format(b) for b in array])

hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)

assert hresult==SCARD_S_SUCCESS

hresult, readers = SCardListReaders(hcontext, [])

assert len(readers)>0

reader = readers[0]

print '\n###### Hackadl.org.au ######'
print '######    Oh hello.   ######\n'

readerstates = []
for i in xrange(len(readers)):
    readerstates += [ (readers[i], SCARD_STATE_UNAWARE) ]
hresult, newstates = SCardGetStatusChange(hcontext, 0, readerstates)

while True:
  hresult, newstates = SCardGetStatusChange(hcontext, 5, newstates)
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
      print 'ID:', hexarray(response), "\n"


      # TODO: POST the card data
      # url = 'http://hackadl.org/checkin'
      # data = urllib.urlencode({'atr' : atr, 'id' : response})
      # content = urllib2.urlopen(url, data).read()
      # print content

    elif eventstate & SCARD_STATE_EMPTY:
      print 'Reader empty\n'

    else:
      print 'Unknown event state', eventstate
