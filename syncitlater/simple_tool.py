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

"""Simple Instapaper<->Pocket sync tool"""
import tempfile, os
import json
import sync, pocket, instapaper
import settings
import logging

class SimpleSync:
    def __init__(self, statefile):
        self.statefile = statefile

    def load_state(self):
        if os.path.exists(self.statefile):
            self.state = json.load(open(self.statefile, 'r'))
        else:
            self.state = {}

    def save_state(self):
        tmpfile = tempfile.mktemp(self.statefile + '.tmp.XXXXXX')
        try:
            json.dump(self.state, open(tmpfile, 'w'))
            os.rename(tmpfile, self.statefile)
        finally:
            try:
                os.unlink()
            except:
                pass

    def synchronize(self, args):
        import settings
        self.load_state()
        self.state.setdefault('member_states', [{}, {}])
        self.state.setdefault('api_states', [{}, {}])
        self.state.setdefault('engine_state', {})

        pocketapi = pocket.PocketApi(settings.POCKET_API_KEY, self.state['api_states'][0])
        print 'Testing Pocket API:',
        sys.stdout.flush()
        if pocketapi.test_auth():
            print 'OK'
        else:
            print 'Failed.'
            pocketapi.reset_auth()
            url = pocketapi.start_auth('http://raisama.net/pocket_test')
            print 'Opening URL: %s' % (url)
            os.spawnlp(os.P_NOWAIT, 'open', 'open', url)
            while True:
                r = raw_input('Has the Pocket authentication finished? (y/n) ')
                if r.lower().startswith('y'):
                    break
            pocketapi.auth_finished()
            if not pocketapi.test_auth():
                print "Something is really wrong: I still can't talk to the Pocket service. :-("
                print "Aborting."
                return 1
            self.save_state()

        instapaperapi = instapaper.InstapaperApi(settings.INSTAPAPER_API_KEY, settings.INSTAPAPER_API_SECRET, self.state['api_states'][1])
        print 'Testing Instapaper API:',
        sys.stdout.flush()
        if instapaperapi.test_auth():
            print 'OK'
        else:
            print 'Failed.'
            import getpass
            instapaperapi.reset_auth()
            username = raw_input('Instapaper Username: ')
            password = getpass.getpass('Instapaper Password: ')
            instapaperapi.authenticate(username, password)
            if not instapaperapi.test_auth():
                print "Something is really wrong: I still can't talk to the Instapaper API. :-("
                print "Aborting."
                return 1
            self.save_state()

        m1 = sync.PocketMember(pocketapi, self.state['member_states'][0])
        m2 = sync.InstapaperMember(instapaperapi, self.state['member_states'][1])
        engine = sync.SyncEngine(self.state['engine_state'], [m1, m2])
        result = list(engine.calculate_sync())

        counts = [{} for r in result]
        for i,(member, changes) in enumerate(result):
            print 'member: %r' % (member)
            print 'changes:'
            for c in changes:
                print '%r' % (c)
                counts[i].setdefault(c['state'], 0)
                counts[i][c['state']] += 1
            print '---'
        print 'Summary:'
        for (member, changes), ct in zip(result, counts):
            print 'member: %r, %d changes [%s]' % (member, len(changes), ', '.join(['%s: %d' % (k, c) for k,c in ct.items()]))

        if args.interactive:
            r = raw_input('Commit? (y/n) ')
            args.dry_run = (not r.lower().startswith('y'))

        if not args.dry_run:
            engine.commit_sync(result)
            self.save_state()

def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description='Simple Instapaper <-> Pocket sync tool')
    parser.add_argument('-i', '--interactive', dest='interactive', action='store_true')
    parser.add_argument('-X', '--commit', dest='dry_run', action='store_false', default=True)
    parser.add_argument('-n', '--dry-run', dest='dry_run', action='store_true', default=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true')
    args = parser.parse_args(argv[1:])

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    s = SimpleSync('simplesync.json')
    return s.synchronize(args)

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
