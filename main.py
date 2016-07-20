
import os
import signal
from microphone import Microphone
from bing_recognizer import *
from player import Player
import pyaudio
import sys
try:
    from creds import BING_KEY
except ImportError:
    print('Get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key')
    sys.exit(-1)

script_dir = os.path.dirname(os.path.realpath(__file__))

hi = os.path.join(script_dir, 'audio/hi.wav')

recognizer = BingVoiceRecognizer(BING_KEY)

mission_completed = False
awake = False

pa = pyaudio.PyAudio()
mic = Microphone(pa)
player = Player(pa)


def handle_int(sig, frame):
    global mission_completed
    
    mission_completed = True
    mic.close()


signal.signal(signal.SIGINT, handle_int)

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
    except UnknownValueError:
        print("Microsoft Bing Voice Recognition could not understand audio")
    except RequestError as e:
        print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))

    awake = False
