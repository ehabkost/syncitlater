import unittest
from syncitlater.tests import instapaper_sync, pocket_sync, sync_algorithm

MODS = [instapaper_sync, pocket_sync, sync_algorithm]

def tests_from_mod(loader, m):
    lt = getattr(m, 'load_tests', None)
    if lt:
        return lt(loader)
    else:
        return loader.loadTestsFromModule(m)

def load_tests(loader, *args):
   s = unittest.TestSuite()
   for mod in MODS:
        msuite = tests_from_mod(loader, mod)
        s.addTest(msuite)
   return s
