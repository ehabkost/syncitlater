
import instapaper, pocket


class SyncMember(object):
	def __init__(self, state):
		self.state = state

	def get_changes(self):
		"""Return changes since the last synchronization"""
		raise NotImplementedError()


class InstapaperMember(SyncMember):
	def __init__(self, api, state):
		self.api = api
		super(InstapaperMember, self).__init__(state)

	def _have(self):
		"""Generate 'have' argument for instalaper API call"""
		items = []
		for i in self.state.get('known_bookmarks', []):
			items.append('%s:%s' % (i['bookmark_id'], i['hash']))
		return ','.join(items)

	def get_changes(self):
		bookmarks = self.api.list_bookmarks(have=self._have())
		for b in bookmarks:
			yield dict(url=b['url'], state='unread')
