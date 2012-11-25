import os
import urllib2, urllib, urlparse
import json
import oauth2

import logging
logger = logging.getLogger(__name__)
info = logger.info
dbg = logger.debug

API_BASE = 'https://www.instapaper.com/api/1/'

def api_url(p, *args, **kwargs):
    u = urlparse.urljoin(API_BASE, p)
    if args or kwargs:
        u += '?' + urllib.urlencode(args + kwargs.items())
    return u


# sample items:
# {u'hash': u'JhXkmQyM', u'description': u'', u'title': u'Americana Boca Suja: Harden the fuck up', u'url': u'http://americanabocasuja.blogspot.com.br/2009/09/harden-fuck-up.html', u'progress_timestamp': 0, u'bookmark_id': 335256617, u'time': 1352099686, u'progress': 0, u'starred': u'0', u'type': u'bookmark', u'private_source': u''},
# {u'hash': u'Qmy2utLt', u'description': u'', u'title': u'Fish: the friendly interactive shell | Ars Technica', u'url': u'http://arstechnica.com/information-technology/2005/12/linux-20051218/2/', u'progress_timestamp': 0, u'bookmark_id': 334677730, u'time': 1351873721, u'progress': 0, u'starred': u'0', u'type': u'bookmark', u'private_source': u''},
# {u'hash': u'lngzG7pK', u'description': u'', u'title': u'Intel declares Clover Trail Atom processor a \u201cno Linux\u201d zone | Ars Technica', u'url': u'http://arstechnica.com/information-technology/2012/09/intel-declares-clover-trail-atom-processor-a-no-linux-zone/', u'progress_timestamp': 0, u'bookmark_id': 323501408, u'time': 1351725307, u'progress': 0, u'starred': u'0', u'type': u'bookmark', u'private_source': u''},
# {u'hash': u'sfhaOra3', u'description': u'Space', u'title': u"Why We Can't Solve Big Problems | MIT Technology Review", u'url': u'http://www.technologyreview.com/featuredstory/429690/why-we-cant-solve-big-problems/', u'progress_timestamp': 0, u'bookmark_id': 334136479, u'time': 1351705881, u'progress': 0, u'starred': u'0', u'type': u'bookmark', u'private_source': u''}

class InstapaperApi:
    def __init__(self, key, secret, state=None):
        """Constructor

        The state object is a dictionary-like object, that will be
        changed by the InstapaperApi in-place.
        """
        self._consumer_key = key
        self._consumer_secret = secret
        if state is None:
            state = {}
        self.state = state

    def make_request(self, p, raw=False, **kwargs):
        """Make authenticated POST request"""
        c = oauth2.Client(self.oauth_consumer(), self.oauth_token())
        u = api_url(p)
        d = urllib.urlencode(kwargs)
        dbg('making post request: url: %r, data: %r', u, d)
        resp,content = c.request(u, 'POST', d)
        dbg('returned data: %r', content)
        return json.loads(content)

    def oauth_consumer(self):
        return oauth2.Consumer(key=self._consumer_key, secret=self._consumer_secret)

    def oauth_token(self):
        return oauth2.Token(key=self.state['oauth_token'], secret=self.state['oauth_token_secret'])

    def del_state(self, key):
        if self.state.has_key(key):
            del self.state[key]

    def reset_auth(self):
        self.del_state('oauth_token')
        self.del_state('oauth_token_secret')

    def authenticate(self, username, password):
        """Authenticate using username and password
        """
        c = oauth2.Client(self.oauth_consumer())
        args = dict(x_auth_username=username, x_auth_password=password, x_auth_mode='client_auth')
        u = api_url('oauth/access_token')
        dbg('auth url: %r', u)
        resp, content = c.request(u, 'POST', urllib.urlencode(args))
        dbg('auth response contents: %r', content)
        tokendata = dict(urlparse.parse_qsl(content))
        self.state['oauth_token'] = tokendata['oauth_token']
        self.state['oauth_token_secret'] = tokendata['oauth_token_secret']

    def is_authenticated(self):
        return self.state.has_key('oauth_token') and self.state.has_key('oauth_token_secret')

    def test_auth(self):
        """Test authentication

        Returns True if it seems to be working.
        Returns False if it's obviously not working (and needs re-authentication).
        Raises an exception on unexpected errors (probably meaning that it needs re-authentication)
        """
        if not self.is_authenticated():
            return False
        r = self.make_request('account/verify_credentials')
        if len(r) > 0 and r[0].get('type') == 'user' and r[0].has_key('user_id'):
            return True
        else:
            return False

    def list_bookmarks(self, **kwargs):
        return self.make_request('bookmarks/list', **kwargs)

    def add_bookmark(self, url, **kwargs):
        return self.make_request('bookmarks/add', url=url, **kwargs)


# below is just test code:

def run_main(a):
    ok = a.test_auth()
    if not ok:
        import getpass
        a.reset_auth()
        username = raw_input('Username: ')
        password = getpass.getpass('Password: ')
        a.authenticate(username, password)
        assert a.test_auth()
    print repr(a.list_bookmarks())
    print repr(a.list_bookmarks(folder_id='archive'))

def main(argv):
    import settings
    logging.basicConfig(level=logging.DEBUG)
    statefile = 'instapaperstate.json'
    if os.path.exists(statefile):
        f = open(statefile, 'r')
        state = json.load(f)
        info('State file loaded.')
    else:
        info('No state file present, starting from scratch')
        state = {}

    a = InstapaperApi(settings.INSTAPAPER_API_KEY, settings.INSTAPAPER_API_SECRET, state)
    try:
        run_main(a)
    finally:
        info('Saving state file...')
        json.dump(state, open(statefile, 'w'))

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
