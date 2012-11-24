import os
import urllib2, urllib, urlparse
import json

API_BASE = 'https://getpocket.com/v3/'
BROWSER_AUTH_URL = 'https://getpocket.com/auth/authorize'

import logging
logger = logging.getLogger(__name__)
info = logger.info
dbg = logger.debug

def api_url(p, *args, **kwargs):
    u = urlparse.urljoin(API_BASE, p)
    if args or kwargs:
        u += '?' + urllib.urlencode(args + kwargs.items())
    return u


class PocketApi:
        def __init__(self, key, state=None):
            """Constructor

            The state object is a dictionary-like object, that will be
            changed by the PocketApi in-place.
            """
            self._consumer_key = key
            if state is None:
                state = {}
            self.state = state

        def make_post(self, p, **kwargs):
            u = api_url(p)
            d = urllib.urlencode(kwargs)
            dbg('making post request: url: %r, data: %r', u, d)
            f = urllib2.urlopen(u, d)
            return dict(urlparse.parse_qsl(f.read()))

        def _get_request_token(self, redir_uri, state=None):
            args = dict(consumer_key=self._consumer_key, redirect_uri=redir_uri)
            if state is not None:
                args['state'] = state
            r = self.make_post('oauth/request', **args)
            return r['code']

        def reset_auth(self):
            """Reset all authentication data on state"""
            for k in ('request_token','access_token','username'):
                if self.state.has_key(k):
                    del self.state[k]

        def start_auth(self, redir_uri, state=None):
            """Start authentication process

            Returns URL to be opened on browser
            """
            if not self.state.has_key('request_token'):
                self.state['request_token'] = self._get_request_token(redir_uri, state)
            dbg('request token: %r', self.state['request_token'])
            args = dict(request_token=self.state['request_token'], redirect_uri=redir_uri)
            u = BROWSER_AUTH_URL + '?' + urllib.urlencode(args)
            return u

        def auth_finished(self):
            """Call this after the redir_uri was successfully opened"""
            assert self.state.has_key('request_token')
            r = self.make_post('oauth/authorize',
                               consumer_key=self._consumer_key,
                               code=self.state['request_token'])
            self.state['access_token'] = r['access_token']
            self.state['username'] = r['username']

        def is_authenticated(self):
            return self.state.has_key('username') and self.state.has_key('access_token')

        def api_get(self, **kwargs):
            """Generic 'get' API method"""
            assert self.is_authenticated()
            return self.make_post('get',
                                  consumer_key=self._consumer_key,
                                  access_token=self.state['access_token'],
                                  **kwargs)


# below is just test code:

def run_main(a):
    if not a.is_authenticated():
        a.reset_auth()
        url = a.start_auth('http://raisama.net/pocket_test')
        print 'Opening URL: %s' % (url)
        os.spawnlp(os.P_NOWAIT, 'open', 'open', url)
        while True:
            r = raw_input('Has authentication finished? (y/n)')
            if r.lower().startswith('y'):
                break
        a.auth_finished()
    print repr(a.api_get())

def main(argv):
    import settings
    logging.basicConfig(level=logging.DEBUG)
    statefile = 'pocketstate.json'
    if os.path.exists(statefile):
        f = open(statefile, 'r')
        state = json.load(f)
        info('State file loaded.')
    else:
        info('No state file present, starting from scratch')
        state = {}

    a = PocketApi(settings.POCKET_API_KEY, state)
    try:
        run_main(a)
    finally:
        info('Saving state file...')
        json.dump(state, open(statefile, 'w'))

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))