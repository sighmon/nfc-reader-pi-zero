import hashlib
import os
import socket
import uuid
from datetime import datetime

# import pygame
import pytz
import requests
from smartcard.scard import (SCARD_PROTOCOL_T0, SCARD_PROTOCOL_T1,
                             SCARD_S_SUCCESS, SCARD_SCOPE_USER,
                             SCARD_SHARE_SHARED, SCARD_STATE_PRESENT,
                             SCARD_STATE_UNAWARE, SCardConnect,
                             SCardEstablishContext, SCardGetStatusChange,
                             SCardListReaders, SCardStatus, SCardTransmit)

# Constants
MD5_SECRET = os.getenv('MD5_SECRET')
DEVICE_NAME = os.getenv('DEVICE_NAME')
XOS_TAPS_ENDPOINT = os.getenv('XOS_TAPS_ENDPOINT')
READER_MODEL = os.getenv('READER_MODEL')

pytz_timezone = pytz.timezone('Australia/Melbourne')


def get_mac_address():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    mac = ':'.join(mac_num[i:i+2] for i in range(0, 11, 2))
    return mac


def get_ip_address():
    return socket.gethostbyname(socket.gethostname())


ip_address = get_ip_address()
reader_name = DEVICE_NAME or 'nfc-' + ip_address.split('.')[-1]


def datetime_now():
    return datetime.now(pytz_timezone).isoformat()


def generate_md5_for_tap():
    md5_hash = hashlib.md5()
    current_datetime = datetime.now(pytz_timezone)
    datetime_md5_format = current_datetime.strftime("%Y/%m/%d-%H:%M:%S")
    md5_hash.update((MD5_SECRET + datetime_md5_format).encode('utf-8'))
    return md5_hash.hexdigest()


def hex_array(array):
    return "".join(["{:02x}".format(b) for b in array])


# def play_sound(sound_name):
#     current_directory = os.getcwd()
#     if current_directory == "/":
#         # Hard code because of /etc/rc.local
#         current_directory = "/home/pi/code/nfc-reader-pi-zero"
#     file_to_play = current_directory
#     file_to_play += "/" + sound_name + ".mp3"
#     try:
#         pygame.mixer.init()
#         pygame.mixer.music.load(file_to_play)
#         pygame.mixer.music.play()
#     except pygame.error:  # pylint: disable=no-member
#         pass


hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)

assert hresult == SCARD_S_SUCCESS

hresult, readers = SCardListReaders(hcontext, [])

assert readers

reader = readers[0]
timeout = 10  # Timeout when there isn't any input

# Welcome song
# play_sound("startup")

# NFC reader code
readerstates = []
for i in range(len(readers)):
    readerstates += [(readers[i], SCARD_STATE_UNAWARE)]
hresult, newstates = SCardGetStatusChange(hcontext, 0, readerstates)

while True:
    hresult, newstates = SCardGetStatusChange(hcontext, 5000, newstates)
    for reader, eventstate, atr in newstates:
        if eventstate & SCARD_STATE_PRESENT:
            # play_sound('success')
            hresult, hcard, dw_active_protocol = SCardConnect(
                hcontext,
                reader,
                SCARD_SHARE_SHARED,
                SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1
            )
            # Turn off NFC reader default buzzer
            hresult, response = SCardTransmit(
                hcard,
                dw_active_protocol,
                [0xFF, 0x00, 0x52, 0x00, 0x00]
            )
            hresult, reader, state, protocol, atr = SCardStatus(hcard)
            hresult, response = SCardTransmit(
                hcard,
                dw_active_protocol,
                [0xFF, 0xCA, 0x00, 0x00, 0x00]
            )
            if response[-2:] == [0x90, 0x00]:
                tag_id = response[:-2]
                # POST the card data
                data = {
                    'nfc_tag': {
                        'atr': hex_array(atr),
                        'uid': hex_array(tag_id)
                    },
                    'nfc_reader': {
                        'mac_address': get_mac_address(),
                        'reader_ip': ip_address,
                        'reader_name': reader_name,
                        'reader_model': READER_MODEL,
                    },
                    'tap_datetime': datetime_now(),  # ISO8601 format
                    'md5': generate_md5_for_tap()
                }
                response = requests.post(XOS_TAPS_ENDPOINT, json=data)
