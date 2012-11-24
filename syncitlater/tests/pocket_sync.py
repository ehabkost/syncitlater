
from syncitlater import sync
import unittest

class FakePocketApi:
	def api_get(self, **kwargs):
		self.since_arg = kwargs.get('since')
		return self.fake_data

class PocketSyncTest(unittest.TestCase):
	def setUp(self):
		self.state = {}
		self.api = FakePocketApi()
		self.member = sync.PocketMember(self.api, self.state)

	def testNoPreviousSync(self):
		self.api.fake_data = {'list':[
			dict(status='0', resolved_url='http://1.example.com/', time_updated='12345'),
			dict(status='1', resolved_url='http://2.example.com/', time_updated='12336'),
			dict(status='2', resolved_url='http://2_5.example.com/', time_updated='11347'),
			dict(status='0', resolved_url='http://3.example.com/', time_updated='12349'),
			dict(status='1', resolved_url='http://4.example.com/', time_updated='12348'),
		]}
		changes = list(self.member.get_changes())
		self.assertEquals(changes, [
			dict(url='http://1.example.com/', state='unread'),
			dict(url='http://2.example.com/', state='archived'),
			dict(url='http://3.example.com/', state='unread'),
			dict(url='http://4.example.com/', state='archived'),
			])
		self.assertEquals(self.state['last_update_timestamp'], 12349)

	def testLastUpdate(self):
		self.state['last_update_timestamp'] = 1000
		self.api.fake_data = {'list':[]}
		changes = list(self.member.get_changes())
		self.assertEquals(changes, [])
		self.assertEquals(self.api.since_arg, '1000')
		self.assertEquals(self.state['last_update_timestamp'], 1000)
