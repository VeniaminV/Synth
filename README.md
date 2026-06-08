# MIDI Synthesizer
Veniamin Velikoretskikh veniamin@pdx.edu

## What I Did

Built a monophonic sawtooth wave MIDI soft synthesizer in Python. The synth:

- Accepts MIDI note on/off events via a virtual MIDI port (loopMIDI + VMPK on Windows)
- Generates a sawtooth wave at -3 dBFS (amplitude 0.708)
- Applies a fixed AR envelope: 10ms linear attack, 10ms linear release
- Treats zero-velocity NOTE ON as NOTE OFF
- Processes MIDI events only between audio blocks to avoid race conditions
- Outputs audio via sounddevice at 44100 Hz with a 256-sample block size (~5.8ms latency)

## How It Went

Getting the Python environment set up on Windows was the main challenge — python-rtmidi
requires a C++ compiler to build from source. Once that was resolved and loopMIDI was
configured as a virtual MIDI cable between VMPK and the synth, everything worked.
The AR envelope required some care to avoid clicks on legato notes (attack restarts
from current envelope level rather than zero).

## What Is Still To Do

- No bonus features implemented (velocity sensitivity, ADSR, polyphony, alternate waveforms)
- A --midi-device flag for selecting a specific port by name would be useful
- The device number for audio output is currently hardcoded; should auto-detect

## Setup

Install dependencies:

```
pip install mido python-rtmidi sounddevice numpy
```

Run the synth:

```
python synth.py
```

List available MIDI ports:

```
python synth.py --list-ports
```

Requires loopMIDI and VMPK (or any virtual MIDI keyboard) on Windows.

## Files

- `synth.py` — main synthesizer program
- `README.md` — this file
- `SYNTH.mp4` — video demo
