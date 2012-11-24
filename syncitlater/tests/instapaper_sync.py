
from syncitlater import sync
import unittest


class FakeInstapaperApi:
	def list_bookmarks(self, folder_id='unread', **kwargs):
		return self.fake_bookmarks.get(folder_id, [])

class InstapaperSyncTest(unittest.TestCase):
	def setUp(self):
		self.api = FakeInstapaperApi()
		self.state = {}
		self.member = sync.InstapaperMember(self.api, self.state)

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
			dict(type='bookmark', bookmark_id=3, hash='three', url='http://3.example.com/'),
			dict(type='bookmark', bookmark_id=4, hash='four', url='http://4.example.com/'),
		]}
		changes = list(self.member.get_changes())
		self.assertEquals(len(changes), 2)
		self.assertEquals(changes[0]['url'], 'http://3.example.com/')
		self.assertEquals(changes[0]['state'], 'unread')
		self.assertEquals(changes[1]['url'], 'http://4.example.com/')
		self.assertEquals(changes[1]['state'], 'unread')

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
				dict(type='bookmark', bookmark_id=3, hash='six', url='http://3.example.com/'), # moved from archive to unread
			],
			'archive':[
				dict(type='bookmark', bookmark_id=7, hash='five', url='http://7.example.com/'),
				dict(type='bookmark', bookmark_id=8, hash='six', url='http://8.example.com/'),
				dict(type='bookmark', bookmark_id=2, hash='six', url='http://2.example.com/'), # moved from unread to archive
			]}

		changes = list(self.member.get_changes())
		self.assertEquals(len(changes), 6)

		self.assertEquals(changes[0]['url'], 'http://5.example.com/')
		self.assertEquals(changes[0]['state'], 'unread')
		self.assertEquals(changes[1]['url'], 'http://6.example.com/')
		self.assertEquals(changes[1]['state'], 'unread')
		self.assertEquals(changes[2]['url'], 'http://3.example.com/')
		self.assertEquals(changes[2]['state'], 'unread')
		self.assertEquals(changes[3]['url'], 'http://7.example.com/')
		self.assertEquals(changes[3]['state'], 'archived')
		self.assertEquals(changes[4]['url'], 'http://8.example.com/')
		self.assertEquals(changes[4]['state'], 'archived')
		self.assertEquals(changes[5]['url'], 'http://2.example.com/')
		self.assertEquals(changes[5]['state'], 'archived')
