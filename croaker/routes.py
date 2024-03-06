import logging

from bottle import abort, route

from croaker import streamer


@route("/play/<playlist_name>")
def play(playlist_name=None):
    if not streamer.load(playlist_name):
        return
    return "OK"


@route("/skip")
def skip():
    if not streamer.play_next():
        return
    return "OK"


@route("/next_in_queue")
def next_in_queue():
    pl = controller.now_playing()
    logging.debug(pl)
    if not pl:
        abort()
    track1 = pl.current
    controller.play_next()
    controller.now_playing().current
    return "\n".join([str(track1), str(track2)])
