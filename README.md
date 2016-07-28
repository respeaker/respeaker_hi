Hi, Respeaker
=============

mic > keyword spotting (pocketsphinx) > tts (bing) > text parser > [stt >] > speaker

### Get started
1. Get [pocketsphinx acoustic model](https://github.com/respeaker/pocketsphinx_keyword_spotting/tree/master/model/hmm), place the files as the following structure.

  ```
  respeaker_hi
  │  bing_recognizer.py
  │  creds_template.py
  │  main.py
  │  microphone.py
  │  player.py
  │  README.md
  ├─audio
  │      hi.wav
  └─model
      │  respeaker.dic
      └─hmm
          └─en
                  feat.params
                  mdef
                  means
                  noisedict
                  README
                  sendump
                  transition_matrices
                  variances
  ```
  
2. Get a key from # get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key
3. `python main.py`
