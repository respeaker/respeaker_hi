import os
import signal
import sys
import socket

import pyaudio

from bing_voice import *
from microphone import Microphone
from player import Player
from spi import SPI

try:
    from creds import BING_KEY
except ImportError:
    print(
    'Get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key')
    sys.exit(-1)

script_dir = os.path.dirname(os.path.realpath(__file__))

hi = os.path.join(script_dir, 'audio/hi.wav')

spi = SPI()
spi.write('offline\n')

bing = BingVoice(BING_KEY)

mission_completed = False
awake = False

pa = pyaudio.PyAudio()
mic = Microphone(pa)
player = Player(pa)


def check_internet(host="8.8.8.8", port=53, timeout=6):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception as ex:
        print ex.message
        return False


while not check_internet(host="223.6.6.6"):
    pass

spi.write('online\n')


def handle_int(sig, frame):
    global mission_completed

    mission_completed = True
    mic.quit()


signal.signal(signal.SIGINT, handle_int)

while not mission_completed:
    if not awake:
        if mic.detect():
            spi.write('wakeup\n')
            awake = True
            player.play(hi)
        continue

    data = mic.listen()
    spi.write('wait\n')

    # recognize speech using Microsoft Bing Voice Recognition
    try:
        text = bing.recognize(data, language='en-US')
        spi.write('answer\n')
        print('Bing:' + text.encode('utf-8'))
        tts_data = bing.synthesize('you said ' + text)
        player.play_raw(tts_data)
    except UnknownValueError:
        print("Microsoft Bing Voice Recognition could not understand audio")
    except RequestError as e:
        print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))

    spi.write('sleep\n')
    awake = False

mic.close()
