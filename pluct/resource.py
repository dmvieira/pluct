# -*- coding: utf-8 -*-
import sys
import traceback
import requests

from jsonschema import validate, SchemaError, ValidationError

from pluct import schema
from pluct.request import Request
from pluct.schema import Schema


def add_methods(resource, s, auth=None):
    for link in getattr(s, "links", []) or []:
        method = link.get("method", "GET")
        href = link.get("href")
        rel = link.get("rel")
        method_class = Request(method, href, auth, resource)
        setattr(resource, rel, method_class.process)


class Resource(dict):

    def __init__(self, url, data=None, schema=None,
                 auth=None, response=None, timeout=30):
        self.auth = auth
        self.url = url
        self.data = data
        self.schema = schema
        self.timeout = timeout
        self.response = response
        if self.schema:
            if self.is_valid():
                add_methods(self, self.schema, self.auth)
                self.parse_data()

    def __repr__(self):
        return str(self.data)

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, attr):
        if attr in self.data:
            return self.data[attr]
        raise KeyError

    def __contains__(self, item):
        return dict.__contains__(self.data, item)

    def is_valid(self):
        try:
            validate(self.data, self.schema._raw_schema)
        except (SchemaError, ValidationError):
            # FIXME remove line below - used only for debugging purposes
            traceback.print_exc(file=sys.stdout)
            return False
        return True

    def parse_data(self):
        if isinstance(self.data, dict):
            for key, value in self.data.items():
                if isinstance(value, list):
                    data_items = []
                    for item in value:
                        try:
                            prop_items = self.schema.properties[key]['items']
                        except KeyError:
                            break
                        if "$ref" in prop_items:
                            s = schema.get(prop_items['$ref'], self.auth)
                        else:
                            s = Schema(self.url, prop_items)
                        data_items.append(
                            Resource(
                                self.url,
                                data=item,
                                schema=s,
                            )
                        )
                    self.data[key] = data_items


def get(url, auth=None, timeout=30):
    headers = {
        'content-type': 'application/json'
    }
    if auth:
        headers['Authorization'] = '{0} {1}'.format(
            auth['type'], auth['credentials']
        )
    response = requests.get(url, headers=headers, timeout=timeout)
    return from_response(response, auth)


def from_response(response, auth=None):
    try:
        data = response.json()
    except ValueError:
        data = {}
    return Resource(
        url=response.url,
        auth=auth,
        data=data,
        schema=schema.from_header(response.headers, auth),
        response=response
    )
