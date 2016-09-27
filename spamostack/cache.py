from collections import MutableMapping
import leveldb
import os

from client_factory import ClientFactory


class Cache(MutableMapping, object):
    def __init__(self, path='./db'):
        """
        Create instance of `Cache` class

        @param path: Path to the database
        @type path: `str`
        """

        self.db = leveldb.LevelDB(path)
        self.cache = dict()
        self.default_init()
        self.client_factory = ClientFactory()
        self.load()

    # Concrete methods for MutableMapping
    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, value):
        self.db.Put(key, str(value))
        self.cache[key] = value

    def __delitem__(self, key):
        del self.cache[key]

    def __iter__(self):
        return iter(self.cache)

    def __len__(self):
        return len(self.cache)
    # end

    def default_init(self):
        "Default initialization for cache"

        uname = os.environ['OS_USERNAME']

        self.cache["created"]["users"][uname]['password'] = \
            os.environ['OS_PASSWORD']
        self.cache["created"]["users"][uname]['project_name'] = \
            os.environ['OS_TENANT_NAME']
        self.cache["auth_url"] = os.environ['OS_AUTH_URL']
        self.cache["created"]["users"][uname]['project_domain_id'] = 'default'
        self.cache["created"]["users"][uname]['user_domain_id'] = 'default'

    def load(self):
        """Load db into cache"""

        def to_objects(cache_elem, client_name, is_key):
            for key, value in cache_elem.iteritems():
                if isinstance(value, dict):
                    to_objects(value, client_name)
                else:
                    if is_key:
                        cache_elem[key] = eval(value)
                    else:
                        cache_elem[key] = [getattr(self.client_factory,
                                                   client_name).get(id=el)
                                           for el in value]

        for key, value in self.db.RangeIter():
            self.cache[key] = value
            if key == 'created':
                is_key = True
            else:
                is_key = False
            to_objects(eval(self.cache[key]), key, is_key)

    def update(self):
        """Update existing db with data from cache"""

        def to_strings(cache_elem):
            for key, value in cache_elem.iteritems():
                if isinstance(value, dict):
                    to_strings(value)
                elif isinstance(value, list):
                    cache_elem[key] = [str(el.id) for el in value]
                else:
                    cache_elem[key] = str(value)

        batch = leveldb.WriteBatch()
        for key, value in self.cache.iteritems():
            to_strings(self.cache[key])
            self.db.Put(key, str(value))
        self.db.Write(batch, sync=True)
