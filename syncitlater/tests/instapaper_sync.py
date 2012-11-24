
from syncitlater import sync
import unittest


class FakeInstapaperApi:
	def list_bookmarks(self, **kwargs):
		return self.fake_bookmarks

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

	def testGetChanges(self):
		self.state['known_bookmarks'] = [
			dict(bookmark_id=1, hash='one'),
			dict(bookmark_id=2, hash='two')]
		self.api.fake_bookmarks = [
			dict(type='bookmark', bookmark_id=3, hash='three', url='http://3.example.com/'),
			dict(type='bookmark', bookmark_id=4, hash='four', url='http://4.example.com/'),
		]
		changes = list(self.member.get_changes())
		self.assertEquals(len(changes), 2)
		self.assertEquals(changes[0]['url'], 'http://3.example.com/')
		self.assertEquals(changes[0]['state'], 'unread')
		self.assertEquals(changes[1]['url'], 'http://4.example.com/')
		self.assertEquals(changes[1]['state'], 'unread')
