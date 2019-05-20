#!/usr/bin/python3

# Author: Justin Gross
# License: This script is licensed under the GPL license, see LICENSE for more info.

import sys
from getopt import getopt, GetoptError

import http.client
from requests.utils import requote_uri
import json
from base64 import b64encode

def exit_with_help():
  print('[usage] check_app_connected.py -H host -P port -u user -p password -a appname -C channelcount -w threshold -c threshold')
  sys.exit(3)

def main(argv):
  host = '127.0.0.1'
  port = 15672
  username = 'guest'
  password = 'guest'
  app = None
  channel_count = None
  warning = None
  critical = None

  try:
    opts, args = getopt(argv, 'h:H:P:u:p:a:C:w:c:', ['help', 'host=','port=','user=','password=','app=', 'chancount=', 'warning=', 'critical='])
  except GetoptError:
    exit_with_help()

  for opt, arg in opts:
    if opt == '-h':
      print('check_app_connected.py -H host -P port -u user -p password -a appname -C channelcount -w threshold -c threshold')
      sys.exit(3)
    elif opt in ("-H", "--host"):
      host = arg
    elif opt in ("-P", "--port"):
      port = arg
    elif opt in ("-u", "--user"):
      username = arg
    elif opt in ("-p", "--password"):
      password = arg
    elif opt in ("-a", "--app"):
      app = arg
    elif opt in ("-C", "--chancount"):
      try:
        channel_count = int(arg)
      except ValueError:
        print('[error] :', arg, 'is not a valid integer!')
        exit_with_help()
    elif opt in ("-w", "--warning"):
      try:
        warning = int(arg)
      except ValueError:
        print('[error] :', arg, 'is not a valid integer!')
        exit_with_help()
    elif opt in ("-c", "--critical"):
      try:
        critical = int(arg)
      except ValueError:
        print('[error] :', arg, 'is not a valid integer!')
        exit_with_help()

  if app == None:
    print('[error] you must provide an application name expected to be found in client properties of connected client!')
    exit_with_help()

  if channel_count != None and (warning == None and critical == None):
    print('[error] when specifying channel count you must provide at least one threshold!')
    exit_with_help()

  if channel_count == None and (warning != None or critical != None):
    print('[error] when specifying a threshold you must provide an expected channel count!')
    exit_with_help()

  if warning != None and critical != None and warning > critical:
    print('[error] warning must be less than critical!')
    exit_with_help()


  basic_auth = "%s:%s"%(username, password)
  auth = b64encode(basic_auth.encode()).decode("ascii")

  rabbit = http.client.HTTPConnection(host, port)
  headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic %s'% auth
  }
  rabbit.request('GET', '/api/connections', None, headers)
  response = rabbit.getresponse()
  connections_encoded = response.read()
  connections = json.loads(connections_encoded.decode('utf8'))

  if 'error' in connections:
    reason = ''
    if 'reason' in connections:
      reason = connections['reason']
    print('[error] %s, %s'%(connections['reason'], connections['error']))
    sys.exit(3)

  for connection in connections:
    channels = None

    if 'client_properties' in connection:
      client_properties = connection['client_properties']

      if 'app' in client_properties and 'state' in connection:

        if connection['state'] == 'running':
          if channel_count != None:
            if 'name' in connection:
              name = connection['name']
              rabbit_solo = http.client.HTTPConnection(host, port)
              rabbit_solo.request('GET', requote_uri('/api/connections/%s/channels'%(name)), None, headers)
              response = rabbit_solo.getresponse()
              channels_encoded = response.read()
              channels = json.loads(channels_encoded.decode('utf8'))
              num_of_chans = len(channels)
              status = 'is connected with %d channels'%(num_of_chans)
            
            chan_count_diff = channel_count - num_of_chans

            if (chan_count_diff != 0):
              if critical == None and warning == None:
                print('[CRITICAL] %s is connected with %d %s %s than expected!'%(app, diff, more_or_less, channel_txt))
                sys.exit(2)

              diff = abs(chan_count_diff)
              channel_txt = 'channels' if diff > 1 else 'channel'
              more_or_less = 'more' if chan_count_diff < 0 else 'less'
              if critical != None and diff >= critical:
                print('[CRITICAL] %s is connected with %d %s %s than expected!'%(app, diff, more_or_less, channel_txt))
                sys.exit(2)

              if warning != None and diff >= warning:
                print('[WARNING] %s is connected with %d %s %s than expected!'%(app, diff, more_or_less, channel_txt))
                sys.exit(1)
              
              print('[OK] %s is connected but with %d %s %s than expected.'%(app, diff, more_or_less, channel_txt))
              sys.exit(0)

            print('[OK] %s is connected with %d channels.'% (app, num_of_chans))
            sys.exit(0)
          
          print('[OK] %s is connected.'%(app))
          sys.exit(0)
        else:
          print('[CRITICAL] %s is not connected!')
          sys.exit(2)

  print('Unknown error occurred!')
  sys.exit(1)
if __name__ == "__main__":
   main(sys.argv[1:])
