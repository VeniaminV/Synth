"""
Veniamin Velikoretskikh veniamin@pdx.edu

synth.py — Sawtooth wave monophonic MIDI synthesizer
CS416 computer music and sound 
"""

import numpy as np
import sounddevice as sd
import mido
import argparse
import threading
import queue
import sys

# Audio constants
SAMPLE_RATE = 44100
BLOCK_SIZE = 256          # ~5.8ms latency at 44100 Hz
AMPLITUDE = 0.708         # -3 dBFS

ATTACK_SAMPLES = int(0.010 * SAMPLE_RATE)   # 10 ms attack
RELEASE_SAMPLES = int(0.010 * SAMPLE_RATE)  # 10 ms release


def midi_note_to_freq(note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


"""
Track the current note's frequency and phase
Run the AR envelope
Generate samples
"""
class SawtoothSynth:
    """Monophonic sawtooth synthesizer with AR envelope."""

    def __init__(self):
        self.sample_rate = SAMPLE_RATE
        self.phase = 0.0
        self.freq = 0.0

        self.env_value = 0.0
        self.env_phase = 'idle'
        self.env_counter = 0

        self.note_on = False
        self.current_note = None

        self._lock = threading.Lock()

    def note_on_event(self, note: int):
        with self._lock:
            self.freq = midi_note_to_freq(note)
            self.current_note = note
            self.note_on = True
            self.env_phase = 'attack'
            remaining = 1.0 - self.env_value
            if remaining <= 0:
                self.env_counter = 0
            else:
                self.env_counter = int(ATTACK_SAMPLES * remaining)

    def note_off_event(self):
        with self._lock:
            self.note_on = False
            self.env_phase = 'release'
            self.env_counter = int(RELEASE_SAMPLES * self.env_value)

    def generate(self, n_frames: int) -> np.ndarray:
        """Generate n_frames samples of audio."""
        out = np.zeros(n_frames, dtype=np.float32)

        with self._lock:
            freq = self.freq
            phase = self.phase
            env_value = self.env_value
            env_phase = self.env_phase
            env_counter = self.env_counter

        if env_phase == 'idle' or freq == 0.0:
            return out  # fixed: don't write stale locals back

        phase_inc = freq / self.sample_rate

        for i in range(n_frames):
            if env_phase == 'attack':
                if env_counter > 0:
                    env_value += 1.0 / ATTACK_SAMPLES
                    env_value = min(env_value, 1.0)
                    env_counter -= 1
                else:
                    env_value = 1.0
                    env_phase = 'sustain'
            elif env_phase == 'release':
                if env_counter > 0:
                    env_value -= 1.0 / RELEASE_SAMPLES
                    env_value = max(env_value, 0.0)
                    env_counter -= 1
                else:
                    env_value = 0.0
                    env_phase = 'idle'

            sample = (2.0 * phase - 1.0) * AMPLITUDE * env_value
            out[i] = sample

            phase += phase_inc
            if phase >= 1.0:
                phase -= 1.0

            if env_phase == 'idle':
                break

        with self._lock:
            self.phase = phase
            self.env_value = env_value
            self.env_phase = env_phase
            self.env_counter = env_counter

        return out


"""
glues everything together
Opens the MIDI port and listens for events
Opens the audio output stream
Passes MIDI events to SawtoothSynth via the queue
"""
class MidiSynth:
    def __init__(self):
        self.synth = SawtoothSynth()
        self.midi_queue = queue.Queue()
        self.running = True

    def audio_callback(self, outdata, frames, time, status):
        """sounddevice callback — runs in audio thread."""
        if status:
            print(f"Audio status: {status}")  # will show errors
        while True:
            try:
                msg = self.midi_queue.get_nowait()
                self._handle_midi(msg)
            except queue.Empty:
                break

        samples = self.synth.generate(frames)
        outdata[:, 0] = samples
        if outdata.shape[1] > 1:
            outdata[:, 1] = samples

    def _handle_midi(self, msg):
        if msg.type == 'note_on':
            if msg.velocity == 0:
                self.synth.note_off_event()
            else:
                self.synth.note_on_event(msg.note)
        elif msg.type == 'note_off':
            self.synth.note_off_event()

    def run(self, midi_port_name=None):
        available = mido.get_input_names()
        if not available:
            print("No MIDI input ports found.", file=sys.stderr)
            print("Try: loopMIDI + VMPK on Windows.", file=sys.stderr)
            sys.exit(1)

        if midi_port_name:
            port_name = midi_port_name
        else:
            print("Available MIDI ports:")
            for i, name in enumerate(available):
                print(f"  [{i}] {name}")
            port_name = available[0]
            print(f"Using: {port_name}")

        print(f"Opening audio output at {SAMPLE_RATE} Hz, block size {BLOCK_SIZE}...")

        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=2,
            dtype='float32',
            callback=self.audio_callback,
            device=3,  # Speakers (Realtek)
        ):
            print(f"Opening MIDI port: {port_name}")
            with mido.open_input(port_name) as port:
                print("Ready. Play notes! Press Ctrl+C to stop.")
                try:
                    for msg in port:
                        if not self.running:
                            break
                        if msg.type in ('note_on', 'note_off'):
                            self.midi_queue.put(msg)
                except KeyboardInterrupt:
                    print("\nStopping.")


def main():
    parser = argparse.ArgumentParser(description="Sawtooth MIDI Synthesizer")
    parser.add_argument(
        '--list-ports', action='store_true',
        help="List available MIDI input ports and exit"
    )
    args = parser.parse_args()

    if args.list_ports:
        ports = mido.get_input_names()
        if ports:
            print("Available MIDI input ports:")
            for p in ports:
                print(f"  {p}")
        else:
            print("No MIDI input ports found.")
        return

    synth = MidiSynth()
    synth.run()


if __name__ == '__main__':
    main()