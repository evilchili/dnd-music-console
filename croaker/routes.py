from bottle import route

from croaker import controller


@route("/play/<playlist_name>")
def play(playlist_name=None):
    if not controller.play_next(playlist_name):
        return
    return "OK"


@route("/skip")
def skip():
    if not controller.play_next():
        return
    return "OK"
