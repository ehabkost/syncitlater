
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

	def _find_known_bookmark(self, url):
		for b in self.state.get('known_bookmarks', []):
			if b.get('url') == url:
				return b

	def _add_known_bookmark(self, b, folder_id):
		entry = self._find_known_bookmark(b['url'])
		if entry is None:
			entry = dict(url=b['url'])
			self.state.setdefault('known_bookmarks', []).append(entry)
		entry.update(url=b['url'], bookmark_id=b['bookmark_id'], hash=b['hash'], folder_id=folder_id)

	def get_changes(self):
		unread = self.api.list_bookmarks(have=self._have('unread'), folder_id='unread')
		for b in unread:
			yield dict(url=b['url'], state='unread')
			self._add_known_bookmark(b, 'unread')
		archived = self.api.list_bookmarks(have=self._have('archive'), folder_id='archive')
		for b in archived:
			yield dict(url=b['url'], state='archived')
			self._add_known_bookmark(b, 'archive')

	def commit_changes(self, changes):
		folder_map = dict(unread='unread', archived='archive')
		for c in changes:
			folder = folder_map[c['state']]
			r = self.api.add_bookmark(url=c['url'], folder_id=folder)
			self._add_known_bookmark(r, folder)
