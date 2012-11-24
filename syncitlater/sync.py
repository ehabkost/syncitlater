
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

	def _have(self, folder_id='unread'):
		"""Generate 'have' argument for instalaper API call"""
		items = []
		for i in self.state.get('known_bookmarks', []):
			if i.get('folder_id', 'unread') == folder_id:
				items.append('%s:%s' % (i['bookmark_id'], i['hash']))
		return ','.join(items)

	def get_changes(self):
		unread = self.api.list_bookmarks(have=self._have('unread'), folder_id='unread')
		for b in unread:
			yield dict(url=b['url'], state='unread')
		archived = self.api.list_bookmarks(have=self._have('archive'), folder_id='archive')
		for b in archived:
			yield dict(url=b['url'], state='archived')
