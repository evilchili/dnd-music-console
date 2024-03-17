from pathlib import Path
from unittest.mock import MagicMock

import io
import queue
import threading

import pytest
import shout

from croaker import streamer, playlist


def get_stream_output(stream):
    stream.seek(0, 0)
    return stream.read()


@pytest.fixture(scope='session')
def silence_bytes():
    return (Path(streamer.__file__).parent / 'silence.mp3').read_bytes()


@pytest.fixture
def output_stream():
    return io.BytesIO()


@pytest.fixture
def mock_shout(output_stream, monkeypatch):
    def handle_send(buf):
        output_stream.write(buf)
    mm = MagicMock(spec=shout.Shout, **{
        'return_value.send.side_effect': handle_send
    })
    monkeypatch.setattr('shout.Shout', mm)
    return mm


@pytest.fixture
def input_queue():
    return queue.Queue()

@pytest.fixture
def skip_event():
    return threading.Event()


@pytest.fixture
def stop_event():
    return threading.Event()


@pytest.fixture
def load_event():
    return threading.Event()


@pytest.fixture
def audio_streamer(mock_shout, input_queue, skip_event, stop_event, load_event):
    return streamer.AudioStreamer(input_queue, skip_event, stop_event, load_event)


def test_streamer_stop(audio_streamer, stop_event, output_stream):
    stop_event.set()
    audio_streamer.do_one_loop()
    assert not stop_event.is_set()


def test_streamer_skip(audio_streamer, skip_event, output_stream):
    skip_event.set()
    audio_streamer.do_one_loop()
    assert not skip_event.is_set()


def test_streamer_load(audio_streamer, load_event, output_stream):
    load_event.set()
    audio_streamer.do_one_loop()
    assert not load_event.is_set()


def test_clear_queue(audio_streamer, input_queue):
    pl = playlist.Playlist(name='test_playlist')
    for track in pl.tracks:
        input_queue.put(bytes(track))
    assert input_queue.not_empty
    audio_streamer.clear_queue()
    assert input_queue.empty


def test_streamer_defaults_to_silence(audio_streamer, input_queue, output_stream, silence_bytes):
    audio_streamer.do_one_loop()
    track = playlist.Playlist(name='test_playlist').tracks[0]
    input_queue.put(bytes(track))
    audio_streamer.do_one_loop()
    audio_streamer.do_one_loop()
    assert get_stream_output(output_stream) == silence_bytes + track.read_bytes() + silence_bytes


def test_streamer_plays_silence_on_error(monkeypatch, audio_streamer, input_queue, output_stream, silence_bytes):
    monkeypatch.setattr(audio_streamer, 'play_file', MagicMock(side_effect=Exception))
    track = playlist.Playlist(name='test_playlist').tracks[0]
    input_queue.put(bytes(track))
    audio_streamer.do_one_loop()
    assert get_stream_output(output_stream) == silence_bytes

def test_streamer_plays_from_queue(audio_streamer, input_queue, output_stream):
    pl = playlist.Playlist(name='test_playlist')
    expected = b''
    for track in pl.tracks:
        input_queue.put(bytes(track))
        expected += track.read_bytes()
    while not input_queue.empty():
        audio_streamer.do_one_loop()
    assert get_stream_output(output_stream) == expected


def test_streamer_handles_stop_interrupt(audio_streamer, output_stream, stop_event):
    stop_event.set()
    audio_streamer.silence.seek(0, 0)
    audio_streamer.play_from_stream(audio_streamer.silence)
    assert get_stream_output(output_stream) == b''


def test_streamer_handles_load_interrupt(audio_streamer, input_queue, output_stream, load_event):
    pl = playlist.Playlist(name='test_playlist')
    input_queue.put(bytes(pl.tracks[0]))
    load_event.set()
    audio_streamer.silence.seek(0, 0)
    audio_streamer.play_from_stream(audio_streamer.silence)
    assert get_stream_output(output_stream) == b''
    assert input_queue.empty
