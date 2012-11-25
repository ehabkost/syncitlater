# Sync It Later
# Copyright (c) 2012 Eduardo Habkost <ehabkost@raisama.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import urllib2, urllib, urlparse
import json

import logging
logger = logging.getLogger(__name__)
info = logger.info
dbg = logger.debug

API_BASE = 'https://getpocket.com/v3/'
BROWSER_AUTH_URL = 'https://getpocket.com/auth/authorize'

def api_url(p, *args, **kwargs):
    u = urlparse.urljoin(API_BASE, p)
    if args or kwargs:
        u += '?' + urllib.urlencode(args + kwargs.items())
    return u


class PleaseReauthenticate(Exception):
    pass

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
        d = json.dumps(kwargs)
        dbg('making post request: url: %r, data: %r', u, d)
        r = urllib2.Request(u)
        r.add_data(d)
        r.add_header('Content-Type', 'application/json; charset=UTF8')
        r.add_header('X-Accept', 'application/json')
        dbg('urllib2 request: %r, headers: %r', r, r.header_items())
        try:
            f = urllib2.urlopen(r)
            s = f.read()
        except urllib2.HTTPError,e:
            if e.code == 401:
                raise PleaseReauthenticate()
            else:
                raise
        dbg('returned data: %r', s)
        return json.loads(s)

    def _get_request_token(self, redir_uri, state=None):
        args = dict(consumer_key=self._consumer_key, redirect_uri=redir_uri)
        if state is not None:
            args['state'] = state
        r = self.make_post('oauth/request', **args)
        return r['code']

    def del_state(self, key):
        if self.state.has_key(key):
            del self.state[key]

    def reset_auth(self):
        """Reset all authentication data on state"""
        self.del_state('request_token')
        self.del_state('access_token')
        self.del_state('username')

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

    def authenticated_post(self, p, **kwargs):
        assert self.is_authenticated()
        return self.make_post(p,
                              consumer_key=self._consumer_key,
                              access_token=self.state['access_token'],
                              **kwargs)

    def api_get(self, **kwargs):
        """Generic 'get' API method"""
        return self.authenticated_post('get', **kwargs)

    def send_actions(self, actions):
        return self.authenticated_post('send', actions=json.dumps(actions))

    def test_auth(self):
        """Test authentication

        Returns True if it seems to be working.
        Returns False if it's obviously not working (and needs re-authentication).
        Raises an exception on unexpected errors (probably meaning that it needs re-authentication)
        """
        if not self.is_authenticated():
            return False
        try:
            self.api_get(count=0)
        except PleaseReauthenticate:
            return False
        return True

# below is just test code:

def run_main(a):
    ok = a.test_auth()
    if not ok:
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
