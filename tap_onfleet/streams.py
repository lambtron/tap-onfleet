
# 
# Module dependencies.
# 

import os
import json
import datetime
import pytz
import singer
from singer import metadata
from singer import utils
import time
from singer.metrics import Point
from dateutil.parser import parse
from tap_onfleet.context import Context


logger = singer.get_logger()
KEY_PROPERTIES = ['id']


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def needs_parse_to_date(string):
    if isinstance(string, str):
        try: 
            parse(string)
            return True
        except ValueError:
            return False
    return False


class Stream():
    name = None
    replication_method = None
    replication_key = None
    stream = None
    key_properties = KEY_PROPERTIES
    session_bookmark = None


    def __init__(self, client=None):
        self.client = client


    def get_bookmark(self, state):
        return (singer.get_bookmark(state, self.name, self.replication_key)) or Context.config["start_date"]


    def update_bookmark(self, state, value):
        if self.is_bookmark_old(state, value):
            singer.write_bookmark(state, self.name, self.replication_key, value)


    def is_bookmark_old(self, state, value):
        current_bookmark = self.get_bookmark(state)
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(current_bookmark)


    def load_schema(self):
        schema_file = "schemas/{}.json".format(self.name)
        with open(get_abs_path(schema_file)) as f:
            schema = json.load(f)
        return schema


    def load_metadata(self):
        schema = self.load_schema()
        mdata = metadata.new()

        mdata = metadata.write(mdata, (), 'table-key-properties', self.key_properties)
        mdata = metadata.write(mdata, (), 'forced-replication-method', self.replication_method)

        if self.replication_key:
            mdata = metadata.write(mdata, (), 'valid-replication-keys', [self.replication_key])

        for field_name in schema['properties'].keys():
            if field_name in self.key_properties or field_name == self.replication_key:
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
            else:
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'available')

        return metadata.to_list(mdata)


    def is_selected(self):
        return self.stream is not None


    # The main sync function.
    def sync(self, state):
        get_data = getattr(self.client, self.name)
        bookmark = self.get_bookmark(state)
        res = get_data(self.replication_key, bookmark)

        if self.replication_method == "INCREMENTAL":
            try:
                for item in res:
                    self.update_bookmark(state, item[self.replication_key])
                    yield (self.stream, item)

            except (TypeError, KeyError) as e:
                yield (self.stream, res)

        elif self.replication_method == "FULL_TABLE":
            for item in res:
                yield (self.stream, item)
        

class Administrators(Stream):
    name = "administrators"
    replication_method = "INCREMENTAL"
    replication_key = "timeLastModified"
    key_properties = "id"


class Hubs(Stream):
    name = "hubs"
    replication_method = "FULL_TABLE"
    key_properties = "id"


class Organizations(Stream):
    name = "organizations"
    replication_method = "INCREMENTAL"
    replication_key = "timeLastModified"
    key_properties = "id"


class Tasks(Stream):
    name = "tasks"
    replication_method = "INCREMENTAL"
    replication_key = "timeLastModified"
    key_properties = "id"


class Teams(Stream):
    name = "teams"
    replication_method = "INCREMENTAL"
    replication_key = "timeLastModified"
    key_properties = "id"


class Workers(Stream):
    name = "workers"
    replication_method = "INCREMENTAL"
    replication_key = "timeLastModified"
    key_properties = "id"



STREAMS = {
    "administrators": Administrators,
    "hubs": Hubs,
    "organizations": Organizations,
    "tasks": Tasks,
    "teams": Teams,
    "workers": Workers
}






