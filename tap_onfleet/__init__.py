#!/usr/bin/env python3

#
# Module dependencies.
#

import json
import sys
import singer
from singer import metadata
from tap_onfleet.onfleet import Onfleet
from tap_onfleet.discover import discover_streams
from tap_onfleet.sync import sync_stream
from tap_onfleet.streams import STREAMS
from tap_onfleet.context import Context


logger = singer.get_logger()


REQUIRED_CONFIG_KEYS = [
    "start_date",
    "user_agent",
    "api_key",
    "quota_limit"
]


def discover(client):
    logger.info("Starting discover")
    catalog = {"streams": discover_streams(client)}
    json.dump(catalog, sys.stdout, indent=2)
    logger.info("Finished discover")


def stream_is_selected(mdata):
    return mdata.get((), {}).get('selected', False)


def get_selected_streams(catalog):
    selected_stream_names = []
    for stream in catalog.streams:
        mdata = metadata.to_map(stream.metadata)
        if stream_is_selected(mdata):
            selected_stream_names.append(stream.tap_stream_id)
    return selected_stream_names


def sync(client, catalog, state):
    selected_stream_names = get_selected_streams(catalog)

    for stream in catalog.streams:
        stream_name = stream.tap_stream_id

        mdata = metadata.to_map(stream.metadata)

        # if stream_name not in selected_stream_names:
        #     logger.info("%s: Skipping - not selected", stream_name)
        #     continue

        key_properties = metadata.get(mdata, (), 'table-key-properties')
        singer.write_schema(stream_name, stream.schema.to_dict(), key_properties)
        logger.info("%s: Starting sync", stream_name)
        instance = STREAMS[stream_name](client)
        instance.stream = stream
        counter_value = sync_stream(state, instance)
        singer.write_state(state)
        logger.info("%s: Completed sync (%s rows)", stream_name, counter_value)

    singer.write_state(state)
    logger.info("Finished sync")


@singer.utils.handle_top_exception(logger)
def main():
    parsed_args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)

    creds = {
        "start_date": parsed_args.config['start_date'],
        "user_agent": parsed_args.config['user_agent'],
        "api_key": parsed_args.config['api_key'],
        "quota_limit": parsed_args.config['quota_limit']
    }
    client = Onfleet(**creds)
    Context.config = parsed_args.config

    if parsed_args.discover:
        discover(client)
    elif parsed_args.catalog:
        state = parsed_args.state or {}
        sync(client, parsed_args.catalog, state)



