#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/3 17:10
# @Author  : renxiaoming@julive.com
# @Site    : 
# @File    : VAD.py.py
# @Software: PyCharm


import collections
import contextlib
import sys
import wave
from pydub import AudioSegment
import glob
import os

import webrtcvad
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str, default='',help="audio path")
parser.add_argument("--audio_folder", type=str, default='/Users/comjia/Downloads/code/pytorch_seq2seq/audio_preprocess/asr_data',help="audio path")
parser.add_argument("--save_folder", type=str, default='/Users/comjia/Downloads/code/pytorch_seq2seq/audio_preprocess/process_folder_cut_ASR',help="audio path")
parser.add_argument("--audio_length_TH", type=int, default=4,help="audio length threshold")
parser.add_argument("--agg_value", type=int, default=3,help="0 is the least aggressive about filtering out non-speech, 3 is the most aggressive")
opt = parser.parse_args()
print opt


def read_wave(path):
    format_type = path.split(".")[-1]
    if format_type == "wav":
        wav_audio = AudioSegment.from_file(path, format="wav").set_channels(1)
    elif format_type == "mp3":
        wav_audio = AudioSegment.from_file(path, format="mp3").set_channels(1)
    elif format_type == "m4a":
        wav_audio = AudioSegment.from_file(path, format="mp4").set_channels(1)
    else:
        print "formate error !"
        return 0

    return wav_audio.raw_data,wav_audio.frame_rate


def write_wave(path, audio, sample_rate):
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    sys.stdout.write('\n')
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])


def for_dialect_cut(audio_folder ="/Users/comjia/Downloads/code/pytorch_seq2seq/audio_preprocess/asr_data",
                    save_folder="/Users/comjia/Downloads/code/pytorch_seq2seq/audio_preprocess/process_folder_cut_ASR",
                    agg_value = 3):
    file_list = glob.glob(os.path.join(audio_folder,"*.m4a"))

    for file_ in file_list:
        filename_without_suffix = file_.split("/")[-1].split(".")[-2]
        # audio, sample_rate = read_wave(file_)
        wav_audio = AudioSegment.from_file(file_, format="m4a")
        #把声道分开
        sounds = wav_audio.split_to_mono()
        sample_rate = wav_audio.frame_rate

        #对左右声道分别处理
        for index,single_sound_channel in enumerate(sounds):

            vad = webrtcvad.Vad(agg_value)
            #30ms is the frame_duration_length
            frames = frame_generator(30, single_sound_channel.raw_data, sample_rate)
            frames = list(frames)
            #对单声道切割之后的segments
            # 300 is the collection length,the deque can save 10 frames 
            segments = vad_collector(sample_rate, 30, 300, vad, frames)

            for i, segment in enumerate(segments):
                path = '%s/%s_%002d_%d.wav' % (save_folder,filename_without_suffix,i,index)
                print(' Writing %s' % (path,))
                # audio_seg.export(save_name, format="wav")
                write_wave(path, segment, sample_rate)






if __name__ == '__main__':
    for_dialect_cut(audio_folder=opt.audio_folder,save_folder=opt.save_folder,agg_value=opt.agg_value)
