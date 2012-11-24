
import instapaper, pocket


class SyncMember(object):
	def __init__(self, state):
		self.state = state

	def warn(self, message):
		"""Log a warning about a sync operation"""
		self.state.setdefault('warnings', []).append(message)

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
		unread = self.api.list_bookmarks(have=self._have('unread'), limit='500', folder_id='unread')
		for b in unread:
			yield dict(url=b['url'], state='unread')
			self._add_known_bookmark(b, 'unread')
		archived = self.api.list_bookmarks(have=self._have('archive'), limit='500', folder_id='archive')
		for b in archived:
			yield dict(url=b['url'], state='archived')
			self._add_known_bookmark(b, 'archive')

	def commit_changes(self, changes):
		folder_map = dict(unread='unread', archived='archive')
		for c in changes:
			folder = folder_map[c['state']]
			r = self.api.add_bookmark(url=c['url'], folder_id=folder)
			self._add_known_bookmark(r, folder)

class PocketMember(SyncMember):
	def __init__(self, api, state):
		self.api = api
		super(PocketMember, self).__init__(state)

	def cache_item_id(self, url, item_id):
		self.state.setdefault('url_item_ids', {})[url] = item_id

	def get_changes(self):
		states = {'0':'unread', '1':'archived'}
		args = dict(detailType='simple')
		last_update = 0
		if self.state.has_key('last_update_timestamp'):
			last_update = int(self.state['last_update_timestamp'])
			args['since'] = str(last_update)
		items = self.api.api_get(**args)
		for i in items['list']:
			url = i['resolved_url']
			c = dict(url=url)
			state = states.get(str(i['status']))
			if state is None:
				continue
			c['state'] = state
			updated = int(i['time_updated'])
			self.cache_item_id(url, i['item_id'])
			yield c
			if updated > last_update:
				last_update = updated
		self.state['last_update_timestamp'] = last_update

	def find_item_id(self, url):
		"""Find the item ID for a specific URL

		Necessary to allow an item to be archived.
		"""
		return self.state.get('url_item_ids', {}).get(url)

	def commit_changes(self, changes):
		actions = []
		for c in changes:
			if c['state'] == 'unread':
				item_id = self.find_item_id(c['url'])
				if item_id is None:				
					a = dict(action='add', url=c['url'])
				else:
					a = dict(action='add', item_id=item_id)
			elif c['state'] == 'archived':
				item_id = self.find_item_id(c['url'])
				if item_id is None:
					self.warn('Unknown item_id for URL: %r' % (c['url']))
					continue
				a = dict(action='archive', item_id=item_id)
			else:
				continue
			actions.append(a)
		self.api.send_actions(actions)

class SyncEngine:
	def __init__(self, state, members):
		self.state = state
		self.members = members

	def synchronize(self):
		changesets = []
		for m in self.members:
			changesets.append(list(m.get_changes()))

		changesets = zip(self.members, changesets)
		for sourceid,(sm,changes) in enumerate(changesets):
			for destid,dm in enumerate(self.members):
				if sourceid == destid:
					continue
				dm.commit_changes(changes)
