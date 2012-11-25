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

from syncitlater import sync
import unittest


class FakeInstapaperApi:
	def list_bookmarks(self, folder_id='unread', **kwargs):
		return self.fake_bookmarks.get(folder_id, [])

	def add_bookmark(self, url, **kwargs):
		item = dict(url=url)
		item.update(kwargs)
		self.fake_added_bookmarks.append(item)
		return [dict(type='meta', foo='bar'), dict(type='bookmark', url=url, hash=hash(url), bookmark_id=hash(url))]

class InstapaperSyncTest(unittest.TestCase):
	def setUp(self):
		self.api = FakeInstapaperApi()
		self.state = {}
		self.member = sync.InstapaperMember(self.api, self.state)

	def find_known_bookmark(self, url):
		for b in self.state.get('known_bookmarks', []):
			if b.get('url') == url:
				return b

	def testNoKnownBookmarks(self):
		self.assertEquals(self.member._have(), '')

	def testSomeKnownBookmarks(self):
		self.state['known_bookmarks'] = [
			dict(bookmark_id=100, hash='hundred'),
			dict(bookmark_id=200, hash='2hundred')]
		self.assertEquals(self.member._have(), '100:hundred,200:2hundred')

	def testSomeKnownPerFolder(self):
		self.state['known_bookmarks'] = [
			dict(bookmark_id=100, hash='hundred0', folder_id='unread'),
			dict(bookmark_id=200, hash='2hundred0', folder_id='unread'),
			dict(bookmark_id=101, hash='hundred1', folder_id='archive'),
			dict(bookmark_id=201, hash='2hundred1', folder_id='archive')]
		self.assertEquals(self.member._have('unread'), '100:hundred0,200:2hundred0')
		self.assertEquals(self.member._have('archive'), '101:hundred1,201:2hundred1')

	def testGetChanges(self):
		self.state['known_bookmarks'] = [
			dict(bookmark_id=1, hash='one'),
			dict(bookmark_id=2, hash='two')]
		self.api.fake_bookmarks = {'unread':[
			dict(type='meta', foo='bar'),
			dict(type='bookmark', bookmark_id=3, hash='three', url='http://3.example.com/'),
			dict(type='bookmark', bookmark_id=4, hash='four', url='http://4.example.com/'),
		]}
		changes = list(self.member.get_changes())
		self.assertEquals(len(changes), 2)
		self.assertEquals(changes[0]['url'], 'http://3.example.com/')
		self.assertEquals(changes[0]['state'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://3.example.com/')['hash'], 'three')
		self.assertEquals(changes[1]['url'], 'http://4.example.com/')
		self.assertEquals(changes[1]['state'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://4.example.com/')['hash'], 'four')

	def testGetMultifolderChanges(self):
		self.state['known_bookmarks'] = [
			dict(bookmark_id=1, hash='one'),
			dict(bookmark_id=2, hash='two'),
			dict(bookmark_id=3, hash='three'),
			dict(bookmark_id=4, hash='four'),
			]
		self.api.fake_bookmarks = {
			'unread':[
				dict(type='bookmark', bookmark_id=5, hash='five', url='http://5.example.com/'),
				dict(type='bookmark', bookmark_id=6, hash='six', url='http://6.example.com/'),
				dict(type='bookmark', bookmark_id=3, hash='three', url='http://3.example.com/'), # moved from archive to unread
			],
			'archive':[
				dict(type='bookmark', bookmark_id=7, hash='seven', url='http://7.example.com/'),
				dict(type='bookmark', bookmark_id=8, hash='eight', url='http://8.example.com/'),
				dict(type='bookmark', bookmark_id=2, hash='two', url='http://2.example.com/'), # moved from unread to archive
			]}

		changes = list(self.member.get_changes())
		self.assertEquals(len(changes), 6)

		self.assertEquals(changes[0]['url'], 'http://5.example.com/')
		self.assertEquals(changes[0]['state'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://5.example.com/')['hash'], 'five')
		self.assertEquals(self.find_known_bookmark('http://5.example.com/')['folder_id'], 'unread')
		self.assertEquals(changes[1]['url'], 'http://6.example.com/')
		self.assertEquals(changes[1]['state'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://6.example.com/')['hash'], 'six')
		self.assertEquals(self.find_known_bookmark('http://6.example.com/')['folder_id'], 'unread')
		self.assertEquals(changes[2]['url'], 'http://3.example.com/')
		self.assertEquals(changes[2]['state'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://3.example.com/')['hash'], 'three')
		self.assertEquals(self.find_known_bookmark('http://3.example.com/')['folder_id'], 'unread')
		self.assertEquals(changes[3]['url'], 'http://7.example.com/')
		self.assertEquals(changes[3]['state'], 'archived')
		self.assertEquals(self.find_known_bookmark('http://7.example.com/')['hash'], 'seven')
		self.assertEquals(self.find_known_bookmark('http://7.example.com/')['folder_id'], 'archive')
		self.assertEquals(changes[4]['url'], 'http://8.example.com/')
		self.assertEquals(changes[4]['state'], 'archived')
		self.assertEquals(self.find_known_bookmark('http://8.example.com/')['hash'], 'eight')
		self.assertEquals(self.find_known_bookmark('http://8.example.com/')['folder_id'], 'archive')
		self.assertEquals(changes[5]['url'], 'http://2.example.com/')
		self.assertEquals(changes[5]['state'], 'archived')
		self.assertEquals(self.find_known_bookmark('http://2.example.com/')['hash'], 'two')
		self.assertEquals(self.find_known_bookmark('http://2.example.com/')['folder_id'], 'archive')

	def testCommitChanges(self):
		self.api.fake_added_bookmarks = []

		self.member.commit_changes([
				dict(url='http://1.example.com/', state='unread'),
				dict(url='http://2.example.com/', state='unread'),
				dict(url='http://3.example.com/', state='archived'),
			])

		self.assertEquals(self.api.fake_added_bookmarks, [
				dict(url='http://1.example.com/', folder_id='unread'),
				dict(url='http://2.example.com/', folder_id='unread'),
				dict(url='http://3.example.com/', folder_id='archive'),
			])
		self.assertEquals(self.find_known_bookmark('http://1.example.com/')['folder_id'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://2.example.com/')['folder_id'], 'unread')
		self.assertEquals(self.find_known_bookmark('http://3.example.com/')['folder_id'], 'archive')
