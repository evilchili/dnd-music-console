import logging
from dataclasses import dataclass
from functools import cached_property

import bottle
import requests

# needs to be imported to attach routes to the default app
from croaker import routes

assert routes


@dataclass
class Client:
    host: str
    port: int

    @cached_property
    def _session(self):
        return requests.Session()

    @property
    def _routes(self):
        return [r.callback.__name__ for r in bottle.default_app().routes]

    def get(self, uri: str, *args, **params):
        url = f"http://{self.host}:{self.port}/{uri}"
        if args:
            url += "/" + "/".join(args)
        res = self._session.get(url, params=params)
        logging.debug(f"{url = }, {res = }")
        return res

    def __getattr__(self, attr):
        if attr in self._routes:

            def dispatch(*args, **kwargs):
                logging.debug(f"calling attr, {args = }, {kwargs = }")
                return self.get(attr, *args, **kwargs)

            return dispatch
        return self.__getattribute__(attr)
