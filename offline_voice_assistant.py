
import os
import time
from threading import Thread, Event
from microphone import Microphone
from bing_voice import *
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
mic = None
quit_event = Event()

def main():
    global mic, quit_event

    bing = BingVoice(BING_KEY)
    awake = False

    pa = pyaudio.PyAudio()
    mic = Microphone(pa)
    player = Player(pa)

    while not quit_event.is_set():
        if not awake:
            if mic.recognize(keyword='hey respeaker'):
                awake = True
                player.play(hi)
                continue
            else:
                break

        command = mic.recognize(max_phrase_ms=6000, max_wait_ms=6000)
        if command:
            print('recognized: ' + command)
            if command.find('play music') > 0:
                pass

        awake = False

    mic.close()

if __name__ == '__main__':
    thread = Thread(target=main)
    thread.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('\nquit')
            quit_event.set()
            mic.interrupt(True, True)
            break

    thread.join()

