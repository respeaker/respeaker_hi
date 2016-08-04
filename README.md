Hi, ReSpeaker
=============

mic > keyword spotting (pocketsphinx) > tts (bing) > text parser > [stt >] > speaker

### Get started
1. Clone this repo and get [pocketsphinx acoustic model](https://github.com/respeaker/pocketsphinx_keyword_spotting/tree/master/model/hmm), place the files as the following structure.

  ```
  cd /tmp/run/mountd/mmcblk0p1   # suppose we place files to a sd card
  git clone https://github.com/respeaker/respeaker_hi.git
  git clone https://github.com/respeaker/pocketsphinx_keyword_spotting.git
  cp -R pocketsphinx_keyword_spotting/model/hmm respeaker_hi/model
  cd respeaker_hi
  ```
  
2. Get a key from # get a key from https://www.microsoft.com/cognitive-services/en-us/speech-api and create creds.py with the key

  ```
  cp creds_template.py creds.py
  vi creds.py  # add the key and save
  ```

3. Run `python main.py` to start a journey


The files structure will be like:

```
respeaker_hi
│  bing_recognizer.py
│  creds_template.py
│  creds.py
│  main.py
│  microphone.py
│  player.py
│  README.md
├─audio
│      hi.wav
└─model
  │  respeaker.dic
  │  keywords.txt
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