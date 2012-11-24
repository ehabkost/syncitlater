
from syncitlater import sync
import unittest

class FakeMember:
	def __init__(self):
		self.committed_changes = []
		self.fake_changes = []

	def get_changes(self):
		return self.fake_changes

	def commit_changes(self, changes):
		self.committed_changes.extend(changes)

class PocketSyncTest(unittest.TestCase):
	def setUp(self):
		self.state = {}
		self.members = [FakeMember(), FakeMember()]
		self.m1,self.m2 = self.members
		self.engine = sync.SyncEngine(self.state, self.members)

	def testNoChanges(self):
		self.engine.synchronize()
		self.assertEquals(self.m1.committed_changes, [])
		self.assertEquals(self.m2.committed_changes, [])

	def testChangesOneSide(self):
		self.m1.fake_changes = [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		]
		self.engine.synchronize()
		self.assertEquals(self.m1.committed_changes, [])
		self.assertEquals(self.m2.committed_changes, [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		])

	def testChangesOtherSide(self):
		self.m2.fake_changes = [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		]
		self.engine.synchronize()
		self.assertEquals(self.m1.committed_changes, [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		])
		self.assertEquals(self.m2.committed_changes, [])

	def testTwoWayChanges(self):
		self.m1.fake_changes = [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		]
		self.m2.fake_changes = [
			dict(url='http://3.example.com/', state='archived'),
			dict(url='http://4.example.com/', state='unread'),
		]
		self.engine.synchronize()
		self.assertEquals(self.m1.committed_changes, [
			dict(url='http://3.example.com/', state='archived'),
			dict(url='http://4.example.com/', state='unread'),
		])
		self.assertEquals(self.m2.committed_changes, [
			dict(url='http://1.example.com/', state='archived'),
			dict(url='http://2.example.com/', state='unread'),
		])
