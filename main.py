
import os
import signal
from microphone import Microphone
from bing_base import *
from bing_recognizer import *
from bing_tts import *
from player import Player
import pyaudio
import sys
try:
    from creds import BING_KEY
except ImportError:
    print('Get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key')
    sys.exit(-1)

from worker import Worker
import time

script_dir = os.path.dirname(os.path.realpath(__file__))

hi = os.path.join(script_dir, 'audio/hi.wav')

bing = BingBase(BING_KEY)
recognizer = BingVoiceRecognizer(bing)
tts = BingTTS(bing)

mission_completed = False
awake = False

pa = pyaudio.PyAudio()
mic = Microphone(pa)
player = Player(pa)

worker = Worker()
worker.set_tts(tts)
worker.set_player(player)

def handle_int(sig, frame):
    global mission_completed

    print "Terminating..."
    mission_completed = True
    mic.close()
    player.close()
    worker.stop()
    pa.terminate()



signal.signal(signal.SIGINT, handle_int)

worker.start()

while not mission_completed:
    if not awake:
        if mic.detect():
            awake = True
            player.play(hi)
        continue

    data = mic.listen()

    # recognize speech using Microsoft Bing Voice Recognition
    try:
        text = recognizer.recognize(data, language='en-US')
        print('Bing:' + text.encode('utf-8'))
        worker.push_cmd(text)
        # let's go ahead, don't wait the poor slow worker
    except UnknownValueError:
        print("Microsoft Bing Voice Recognition could not understand audio")
    except RequestError as e:
        print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))

    awake = False
