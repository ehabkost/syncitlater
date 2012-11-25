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

class FakePocketApi:
	def __init__(self):
		self.fake_actions = []

	def api_get(self, **kwargs):
		self.since_arg = kwargs.get('since')
		return self.fake_data

	def send_actions(self, actions):
		self.fake_actions.extend(actions)

class PocketSyncTest(unittest.TestCase):
	def setUp(self):
		self.state = {}
		self.api = FakePocketApi()
		self.member = sync.PocketMember(self.api, self.state)

	def testNoPreviousSync(self):
		self.api.fake_data = {'list':{
			'1':   dict(status='0', item_id='1', given_url='http://1.example.com/', time_updated='12345'),
			'2':   dict(status='1', item_id='2', resolved_url='http://2.example.com/', time_updated='12336'),
			'2_5': dict(status='2', item_id='2_5', resolved_url='http://2_5.example.com/', time_updated='11347'),
			'3':   dict(status='0', item_id='3', given_url='http://3.example.com/', time_updated='12349'),
			'4':   dict(status='1', item_id='4', given_url='http://jmp.example.com/foobar', resolved_url='http://4.example.com/', time_updated='12348'),
		}}
		changes = list(self.member.get_changes())
		self.assertEquals(sorted(changes), sorted([
			dict(url='http://1.example.com/', state='unread'),
			dict(url='http://2.example.com/', state='archived'),
			dict(url='http://3.example.com/', state='unread'),
			dict(url='http://4.example.com/', state='archived'),
			]))
		self.assertEquals(self.state['last_update_timestamp'], 12349)
		self.assertEquals(self.member.find_item_id('http://1.example.com/'), '1')
		self.assertEquals(self.member.find_item_id('http://2.example.com/'), '2')
		self.assertEquals(self.member.find_item_id('http://3.example.com/'), '3')
		self.assertEquals(self.member.find_item_id('http://4.example.com/'), '4')

	def testLastUpdate(self):
		self.state['last_update_timestamp'] = 1000
		self.api.fake_data = {'list':{}}
		changes = list(self.member.get_changes())
		self.assertEquals(changes, [])
		self.assertEquals(self.api.since_arg, '1000')
		self.assertEquals(self.state['last_update_timestamp'], 1000)

	def testSimpleCommitChanges(self):
		self.member.commit_changes([
			dict(url='http://1.example.com/', state='unread'),
			dict(url='http://2.example.com/', state='archived'),
		])
		self.assertEquals(self.api.fake_actions, [
			dict(action='add', url='http://1.example.com/'),
		])
		# should have logged a warning about the unknown item_id for the archived item
		self.assertTrue(len(self.member.state['warnings']) > 0)

	def testReaddKnownItem(self):
		self.member.cache_item_id('http://1.example.com/', '1001')
		self.member.commit_changes([
			dict(url='http://1.example.com/', state='unread'),
			dict(url='http://2.example.com/', state='archived'),
		])
		self.assertEquals(self.api.fake_actions, [
			dict(action='add', item_id='1001'),
		])
		# should have logged a warning about the unknown item_id for the archived item
		self.assertTrue(len(self.member.state['warnings']) > 0)

	def testArchiveKnownItem(self):
		self.member.cache_item_id('http://1.example.com/', '1001')
		self.member.cache_item_id('http://2.example.com/', '2001')
		self.member.commit_changes([
			dict(url='http://1.example.com/', state='unread'),
			dict(url='http://2.example.com/', state='archived'),
		])
		self.assertEquals(self.api.fake_actions, [
			dict(action='add', item_id='1001'),
			dict(action='archive', item_id='2001'),
		])
		# should have logged a warning about the unknown item_id for the archived item
		self.assertEquals(len(self.member.state.get('warnings',[])), 0)
