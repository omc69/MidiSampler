# python3 -m pip install python-rtmidi
# python3 -m pip install setuptools --user
# python3 -m pip install cffi --user
# python3 -m pip install sounddevice --user
# python3 -m pip install pydub --user
# libav
# brew install libav
#
# ffmpeg
# brew install ffmpeg
#
# python3 -m pip install scipy
# python3 -m pip install wavio
# https://realpython.com/playing-and-recording-sound-python/#python-sounddevice_1
# https://python-sounddevice.readthedocs.io/en/0.3.3/
# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://tutswiki.com/read-write-config-files-in-python/

# Nfrom __future__ import print_functionNN
from configparser import ConfigParser
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.silence import detect_nonsilent

import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON
from rtmidi.midiutil import open_midioutput
import logging
import os
import sys
import time
import sounddevice as sd
from scipy.io.wavfile import write
from pathlib import Path
import wavio as wv
import numpy
assert numpy

#######################


def MainInit():
    # Logging
    # https://realpython.com/python-logging/
    log = logging.getLogger('midiout')
    logging.basicConfig(level=logging.DEBUG)

    print("*****************************************")
    print("Midisampler")
    print()
    print("2023 by Christian Gehring (Build 2912.23)")
    print("*****************************************")

    config_file = Path("config.ini")
    if config_file.is_file():
        print(str(config_file) + " found")
        # Read config.ini file
        config_object = ConfigParser()
        config_object.read("config.ini")

        # Get MIDI Config
        MIDI = config_object["MIDI"]
        AUDIO = config_object["AUDIO"]
        PATCH = config_object["PATCH"]
        MISC = config_object["MISC"]

        global velo_start
        global note_start
        global note_stop
        global note_step
        global velo_stop
        global velo_step
        global note_length
        global midiport
        global freq
        global Audiochannels
        global folder
        global Vendor
        global Device
        global Patchname
        global workdir
        global AudioDevice

        note_start = int(MIDI["note_start"])
        note_stop = int(MIDI["note_stop"])
        note_length = int(MIDI["note_length"])
        note_step = int(MIDI["note_step"])
        velo_start = int(MIDI["velo_start"])
        velo_stop = int(MIDI["velo_stop"])
        velo_step = int(MIDI["velo_step"])
        midiport = int(MIDI["midiport"])
        freq = int(AUDIO["Samplerate"])
        Audiochannels = int(AUDIO["Channels"])
        AudioDevice = AUDIO["Device"]
        folder = MISC["Folder"]
        Vendor = PATCH["Vendor"]
        Device = PATCH["Device"]
        Patchname = PATCH["Patchname"]

        # Creating Directories for Samples
        workdir = "Samples/" + Vendor + "/" + Device + "/" + Patchname
        os.makedirs(workdir, exist_ok=True)
    else:
        print("config.ini not found. Please run app inside directory.")
        sys.exit(1)

    return
#######################


def get_midiport():
    # Prompts user for MIDI input port, unless a valid port number or name
    # is given as the first argument on the command line.
    # API backend defaults to ALSA on Linux.

    port = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        midiout, port_name = open_midioutput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    note_on = [NOTE_ON, 60, 112]  # channel 1, middle C, velocity 112
    note_off = [NOTE_OFF, 60, 0]

    with midiout:
        print("Sending NoteOn event.")
        midiout.send_message(note_on)
        time.sleep(1)
        print("Sending NoteOff event.")
        midiout.send_message(note_off)
        time.sleep(0.1)

    del midiout

    return
#######################


def get_soundcard():
    print(sd.query_devices())
    sd.default.samplerate = 44100
    print(sd.DeviceList())
    sd.default.device = AudioDevice

    return
#######################


def trimsample():
    # Load your audio file
    sound = AudioSegment.from_wav("temp.wav")

    # Detect non-silent parts
    nonsilent_parts = detect_nonsilent(
        sound,
        min_silence_len=500,  # Minimum length of silence to be considered
        silence_thresh=sound.dBFS-14  # Silence threshold
    )

    # Get start and end of first nonsilent part
    start = nonsilent_parts[0][0] if nonsilent_parts else 0
    end = nonsilent_parts[-1][1] if nonsilent_parts else len(sound)

    # Extract non-silent part
    trimmed_sound = sound[start:end]

    # Export the result
    trimmed_sound.export("trimmed_output.wav", format="wav")

    return
#######################


def get_samplefrommidi():

    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()
    print("Checking MIDI Ports.....")
    print(available_ports)

    if available_ports:
        midiout.open_port(midiport)
    else:
        midiout.open_virtual_port("My virtual output")

    with midiout:
        current_note = note_start
        while current_note <= note_stop:
            current_vel = velo_start
            while current_vel <= velo_stop:

                note_on = [NOTE_ON, current_note, current_vel]
                note_off = [NOTE_OFF, current_note, 0]
                wavfilename = Patchname + "_" + \
                    str(current_note) + "_" + str(current_vel) + ".wav"

                ########### Start MIDI Sampling ###############
                duration = note_length + 0.2     # 0.2s buffer
                recording = sd.rec(int(duration * freq),
                                   samplerate=freq, channels=Audiochannels)

                # Send Midi and Velocity to Midi Port
                time.sleep(0.2)  # Short pause

                print("Sending NoteOn event " +
                      str(current_note) + " " + str(current_vel))
                midiout.send_message(note_on)

                time.sleep(note_length)
                print("Sending NoteOff event.")
                midiout.send_message(note_off)
                time.sleep(1)  # Short pause

                # Wait for Audiodevice and save Audiofile
                sd.wait()
                write(workdir + "/" + wavfilename, freq, recording)

                current_vel = current_vel + velo_step
                #########################################
                # Play Note with last velo (unsauber)
                #########################################
                if current_vel > velo_stop:
                    last_vel = velo_stop
                    note_on = [NOTE_ON, current_note, last_vel]
                    note_off = [NOTE_OFF, current_note, 0]
                    wavfilename = Patchname + "_" + \
                        str(current_note) + "_" + str(last_vel) + ".wav"

                    ########### Start MIDI Sampling ###############
                    duration = note_length + 0.2     # 0.2s buffer
                    recording = sd.rec(int(duration * freq),
                                       samplerate=freq, channels=Audiochannels)

                    # Send Midi and Velocity to Midi Port
                    time.sleep(0.2)  # Short pause

                    print("Sending NoteOn event " +
                          str(current_note) + " " + str(last_vel))
                    midiout.send_message(note_on)

                    time.sleep(note_length)
                    print("Sending NoteOff event.")
                    midiout.send_message(note_off)
                    time.sleep(1)  # Short pause

                    # Wait for Audiodevice and save Audiofile
                    sd.wait()
                    write(workdir + "/" + wavfilename, freq, recording)
                ###############################################

            current_note = current_note + note_step

    del midiout

######################
# MAIN
######################


MainInit()
# get_midiport()
get_soundcard()
get_samplefrommidi()
# trimsample()
