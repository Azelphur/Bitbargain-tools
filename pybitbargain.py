#!/usr/bin/python3


"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import urllib.request
import urllib.parse
import json

STATUS_URL  = "https://bitbargain.co.uk/api/status"
TRADE_URL   = "https://bitbargain.co.uk/api/trades"
ONLINE_URL  = "https://bitbargain.co.uk/api/write/online"
OFFLINE_URL = "https://bitbargain.co.uk/api/write/offline"
BUY_URL     = "https://bitbargain.co.uk/api/buy"

class BitBargain():
    def __init__(self, login, api_key):
        self.login = login
        self.api_key = api_key
        self.setUserAgent()

    def _post(self, URL, data={}):
        data["login"] = self.login
        data["api_key"] = self.api_key
        data = urllib.parse.urlencode(data)
        data = data.encode('utf-8')
        request = urllib.request.Request(URL)
        request.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
        request.add_header("User-Agent", self.agent)
        f = urllib.request.urlopen(request, data, 5)
        response = f.read()
        response = response.decode('utf-8')
        try:
            data = json.loads(response)
        except ValueError:
            print('INVALID JSON %s' % response)
            return False
        return data


    def getTrades(self, **kwargs):
        return self._post(TRADE_URL, kwargs)

    def setUserAgent(self, agent="Library"):
        self.agent = "pyBitBargain (%s)" % (agent)

    def getStatus(self, keepalive=False):
        return self._post(STATUS_URL, {'keepalive' : int(keepalive)})

    def goOnline(self):
        return self._post(ONLINE_URL)

    def goOffline(self):
        return self._post(OFFLINE_URL)

    def getBuys(self):
        return self._post(BUY_URL)
        
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 4:
        print("Usage: ./pybitbargain.py <command> <login> <api_key>")
        print("Available commands: status, status-keepalive, online, offline")
        exit()

    b = BitBargain(sys.argv[2], sys.argv[3])
    b.setUserAgent("Command line tool")

    if sys.argv[1].lower() == 'status':
        print(json.dumps(b.getStatus(), sort_keys=True, indent=4))
    elif sys.argv[1].lower() == 'status-keepalive':
        print(json.dumps(b.getStatus(True), sort_keys=True, indent=4))
    elif sys.argv[1].lower() == 'online':
        print(json.dumps(b.goOnline(), sort_keys=True, indent=4))
    elif sys.argv[1].lower() == 'offline':
        print(json.dumps(b.goOffline(), sort_keys=True, indent=4))
    elif sys.argv[1].lower() == 'trades':
        print(json.dumps(b.getTrades(), sort_keys=True, indent=4))
    else:
        print("Unknown command: %s" % (sys.argv[1]))

