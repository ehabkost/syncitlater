
import copy
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

	def solve_conflict(self, changes):
		urls = set()
		states = set()
		for mid,c in changes:
			urls.add(c['url'])
			states.add(c['state'])
			if set(c.keys()) - set(['url', 'state']):
				# I don't know how to solve conflicts for anything except the 'state' field
				return None
		if len(urls) > 1:
			# to solve conflicts, the URLs should really match
			return None

		url, = urls
		if len(states) == 1:
			state, = states
			# this one is obvious: only one state
			return dict(url=url, state=state)

		# archived items can be unarchived, it won't hurt too much
		states.remove('archived')
		if len(states) == 1:
			state, = states
			return dict(url=url, state=state)

		# anything else, I don't know how to solve
		return None


	@staticmethod
	def different_versions(changes):
		r = []
		for c in changes:
			found = any(v==c for v in r)
			if not found:
				r.append(c)
		return r

	def member_ids(self):
		"""Return list of member IDs (indexes on self.members)"""
		return range(len(self.members))

	def warn(self, msg):
		self.state.setdefault('warnings', []).append(msg)

	def check_for_conflicts(self, url, changes):
		"""Check for conflicts

		If returning None, the changes will be kept as-is.
		If returning a list, the changes will be skipped, and replaced
		by the ones in the list.
		"""
		if len(changes) <= 1:
			return # no conflicts. good!

		def change_skip_member(c, mid):
			"""Make a change be skipped on a specific member"""
			c.setdefault('engine_hints', {}).setdefault('skip_members', []).append(mid)
	
		def skip_member(mid):
			# ask for a member to be skipped for all changes
			for _,c in changes:
				c.setdefault('engine_hints', {}).setdefault('skip_members', []).append(mid)

		different_versions = self.different_versions([c for mid,c in changes])

		if len(different_versions) == 1:
			# everybody agrees. good!
			# make only one change object, and make it skip the members that
			# already agree
			c = different_versions[0]
			for mid,_ in changes:
				change_skip_member(c, mid)
			return [c]
		else:
			conflict_solution = copy.deepcopy(self.solve_conflict(changes))
			if conflict_solution is None:
				self.warn("I don't know how to solve the conflict for URL: %s" % (url))
				return [] # won't send anything anywhere
			for mid,c in changes:
				if c == conflict_solution:
					# this member already agrees with the conflict solution, skip it
					change_skip_member(conflict_solution, mid)
			return [conflict_solution]

	def calculate_sync(self):
		changesets = []
		mids = range(len(self.members))
		changesets = [list(m.get_changes()) for m in self.members]
		extra_changes = []

		# look for conflicts
		per_url = {}
		for mid,changes in enumerate(changesets):
			for c in changes:
				per_url.setdefault(c['url'], []).append( (mid, c) )
		for url,changes in per_url.items():
			r = self.check_for_conflicts(url, changes)
			if r is not None: # changes will be replaced
				for mid,c in changes:
					c.clear() # remove item by clearing it
				extra_changes.extend(r)

		resulting_changes = dict((mid,[]) for mid in mids)
		for sourceid,changes in list(enumerate(changesets))+[(-1, extra_changes)]:
			for c in changes:
				if len(c) == 0:
					continue
				for destid,dm in enumerate(self.members):
					if sourceid == destid:
						continue
					cc = copy.deepcopy(c)
					engine_hints = cc.get('engine_hints', {})
					if cc.has_key('engine_hints'):
						del cc['engine_hints']
					if destid in engine_hints.get('skip_members', []):
						continue # skip this change
					resulting_changes[destid].append(cc)

		for mid,member in enumerate(self.members):
			yield member, resulting_changes[mid]


	def synchronize(self):
		for member, changes in self.calculate_sync():
			member.commit_changes(changes)
