
#
# Module dependencies.
#

from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from singer import utils
import backoff
import requests
import logging
import time
import sys


logger = logging.getLogger()


""" Simple wrapper for Onfleet. """
class Onfleet(object):

  def __init__(self, start_date=None, user_agent=None, api_key=None, quota_limit=50):
    self.user_agent = user_agent
    self.start_date = start_date
    self.quota_limit = quota_limit
    self.api_key = api_key
    self.uri = "https://onfleet.com/api/v2/"


  def _epoch_to_datetime_string(self, milliseconds):
    datetime_string = None
    try:
      datetime_string = time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(milliseconds / 1000))
    except TypeError:
      pass
    return datetime_string


  def _datetime_string_to_epoch(self, datetime_string):
    return utils.strptime_with_tz(datetime_string).timestamp() * 1000


  def _list_epoch_to_datetime_string(self, array):
    for i, v in enumerate(array):
      try:
        array[i] = self._dictionary_epoch_to_datetime_string(v)
      except AttributeError:
        pass
    return array


  def _dictionary_epoch_to_datetime_string(self, dictionary):  
    datetime_keys = [
      "timeCreated",
      "timeLastModified",
      "timeLastSeen",
      "time"
    ]

    for k, v in dictionary.items():
      if isinstance(v, dict):
        dictionary[k] = self._dictionary_epoch_to_datetime_string(v)
      if isinstance(v, list):
        dictionary[k] = self._list_epoch_to_datetime_string(v)
      for datetime_key in datetime_keys:
        if k == datetime_key:
          dictionary[k] = self._epoch_to_datetime_string(v)
    return dictionary


  # Throttling: max is 20 requests per second.
  # http://docs.onfleet.com/docs/throttling
  def _check_rate_limit(self, rate_limit_remaining=None, rate_limit_limit=None):
    if float(rate_limit_remaining) / float(rate_limit_limit) * 100 < float(self.quota_limit):
      time.sleep(2000)


  @backoff.on_exception(backoff.expo,
                        requests.exceptions.RequestException)
  def _get(self, path, bookmark, lastId=None, **kwargs):
    uri = "{uri}{path}".format(uri=self.uri, path=path)
    payload = {
      "from": self._datetime_string_to_epoch(bookmark)
    }
    if lastId is not None:
      payload["lastId"] = lastId

    logger.info("GET request to {uri}".format(uri=uri))
    response = requests.get(uri, auth=HTTPBasicAuth(self.api_key, ''), params=payload)
    response.raise_for_status()
    self._check_rate_limit(response.headers.get('X-RateLimit-Remaining'), response.headers.get('X-RateLimit-Limit'))
    return response.json()
    

  # 
  # Methods to retrieve data per stream/resource.
  # 

  def administrators(self, column_name=None, bookmark=None):
    res = self._get("admins", bookmark)
    return self._list_epoch_to_datetime_string(res)


  def hubs(self, column_name=None, bookmark=None):
    res = self._get("hubs", bookmark)
    return self._list_epoch_to_datetime_string(res)    


  def organizations(self, column_name=None, bookmark=None):
    res = self._get("organization", bookmark)
    try:
      for item in res:
        yield self._dictionary_epoch_to_datetime_string(item)
    except AttributeError:
      yield self._dictionary_epoch_to_datetime_string(res)


  def tasks(self, column_name=None, bookmark=None):
    has_more = True
    last_id = None
    path = "tasks/all"
    from_date = bookmark

    while has_more:
      res = self._get(path, from_date, last_id)
      tasks = res["tasks"]

      try:
        last_id = res["lastId"]
      except KeyError:
        has_more = False
        pass

      for task in tasks:
        new_task = self._dictionary_epoch_to_datetime_string(task)
        from_date = new_task["timeLastModified"]
        yield new_task


  def teams(self, column_name=None, bookmark=None):
    res = self._get("teams", bookmark)
    return self._list_epoch_to_datetime_string(res)


  def workers(self, column_name=None, bookmark=None):
    res = self._get("workers", bookmark)
    return self._list_epoch_to_datetime_string(res)




