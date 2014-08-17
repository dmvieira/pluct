# -*- coding: utf-8 -*-

from cgi import parse_header

from jsonpointer import resolve_pointer

from pluct.datastructures import IterableUserDict


class Schema(IterableUserDict):

    def __init__(self, href, raw_schema=None, session=None):
        self._init_href(href)
        self._data = None
        self._raw_schema = raw_schema
        self.session = session

    def expand_refs(self, item):
        if isinstance(item, dict):
            iterator = item.iteritems()
        elif isinstance(item, list):
            iterator = enumerate(item)
        else:
            return

        for key, value in iterator:
            if isinstance(value, dict) and '$ref' in value:
                item[key] = self.from_href(
                    value['$ref'], raw_schema=self._raw_schema,
                    session=self.session)
                continue
            self.expand_refs(value)

    @property
    def data(self):
        if self._data is None:
            self._data = self.resolve()
        return self._data

    @property
    def raw_schema(self):
        # TODO: remove raw_schema or point to the real raw_schema
        # Pointing seems more useful
        return self.data

    @classmethod
    def from_href(cls, href, raw_schema, session):
        href, url, pointer = cls._split_href(href)
        is_external = url != ''

        if is_external:
            return LazySchema(href, session=session)

        return Schema(href, raw_schema=raw_schema, session=session)

    def resolve(self):
        data = resolve_pointer(self._raw_schema, self.pointer)
        self.expand_refs(data)
        return data

    def get_link(self, name):
        links = self.get('links') or []
        for link in links:
            if link.get('rel') == name:
                return link
        return None

    def _init_href(self, href):
        (self.href, self.url, self.pointer) = self._split_href(href)

    @classmethod
    def _split_href(cls, href):
        parts = href.split('#', 1)
        url = parts[0]

        pointer = ''
        if len(parts) > 1:
            pointer = parts[1] or pointer

        href = '#'.join((url, pointer))

        return href, url, pointer


class LazySchema(Schema):

    def __init__(self, href, session=None):
        self._init_href(href)
        self.session = session
        self._data = None
        self._raw_schema = None

    def resolve(self):
        response = self.session.request('get', self.url)
        self._raw_schema = response.json()
        return Schema.resolve(self)


def get_profile_from_header(headers):
    if 'content-type' not in headers:
        return None

    full_content_type = 'content-type: {0}'.format(headers['content-type'])
    header, parameters = parse_header(full_content_type)

    if 'profile' not in parameters:
        return None

    schema_url = parameters['profile']
    return schema_url
