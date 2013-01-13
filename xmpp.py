import logging
import time
import pybitbargain
import argparse
import pickle
import os

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout

UPDATE_TIME = 10
PICKLE_PATH = 'xmpp.pickle'

def rmZeros(number):
    number = str(number).rstrip('0').rstrip('.')
    return number

class BitBargainBot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        if os.path.exists(PICKLE_PATH):
            self.users = pickle.load(open(PICKLE_PATH, 'rb'))
        else:
            self.users = {}
        f = open(PICKLE_PATH, 'wb')
        pickle.dump(self.users, f)
        f.close()

        self.bbPoll(True)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            addr, jid = str(msg["from"]).split("/")

            args = msg["body"].split()

            if args[0].lower() == 'register':
                if len(args) != 3:
                    msg.reply("Usage: register <username> <api key>").send()
                    return

                status = self.bbGetStatus(args[1], args[2])
                if not status['success']:
                    msg.reply("Failed to register: %s" % (status['response']['msg'])).send()
                    return
                msg.reply("You have registered successfully").send()

                self.users[addr] = {}
                self.users[addr] = { 'user'          : args[1],
                                     'api_key'       : args[2],
                                     'keepalive'     : False,
                                     'seen_trades'   : [],
                                     'status'        : status }
                f = open(PICKLE_PATH, 'wb')
                pickle.dump(self.users, f)
                f.close()
                print('New user! %s' % (addr))

            elif args[0].lower() == 'online':
                if addr not in self.users:
                    msg.reply("You must register first!").send()
                    return
                status = self.bbOnline(self.users[addr]['user'], self.users[addr]['api_key'])
                if not status['success']:
                    msg.reply("Failed to go online: %s" % (status['response']['msg'])).send()
                    return
                msg.reply("You are now online").send()
                self.users[addr]['status']['response']['is_online'] = 1

            elif args[0].lower() == 'offline':
                if addr not in self.users:
                    msg.reply("You must register first!").send()
                    return
                status = self.bbOffline(self.users[addr]['user'], self.users[addr]['api_key'])
                if not status['success']:
                    msg.reply("Failed to go offline: %s" % (status['response']['msg'])).send()
                    return
                msg.reply("You are now offline").send()
                self.users[addr]['status']['response']['is_online'] = 0

            elif args[0].lower() == 'keepalive':
                if addr not in self.users:
                    msg.reply("You must register first!").send()
                    return
                self.users[addr]['keepalive'] = not self.users[addr]['keepalive']
                if self.users[addr]['keepalive']:
                    msg.reply("Keeping the connection alive").send()
                else:
                    msg.reply("Stopping keeping the connection alive!").send()

            else:
                msg.reply("Unknown command, please use register, online, offline or keepalive.").send()


    def bbPoll(self, firstrun=False):
        for addr, data in self.users.items():
            status = self.bbGetStatus(data['user'], data['api_key'], data['keepalive'])
            if not firstrun:
                if data['status']['response']['last_trade_id'] != status['response']['last_trade_id']:
                    self.bbCheckTrades(addr)
                if data['status']['response']['is_online'] != status['response']['is_online']:
                    if status['response']['is_online']:
                        self.send_message(mto=addr, mbody='You are now online')
                    else:
                        self.send_message(mto=addr, mbody='You are now offline')

            data['status'] = status

    def bbGetStatus(self, user, api_key, keepalive=False):
        bb = pybitbargain.BitBargain(user, api_key)
        bb.setUserAgent('XMPP Bot')
        return bb.getStatus()

    def bbOnline(self, user, api_key):
        bb = pybitbargain.BitBargain(user, api_key)
        bb.setUserAgent('XMPP Bot')
        return bb.goOnline()

    def bbOffline(self, user, api_key):
        bb = pybitbargain.BitBargain(user, api_key)
        bb.setUserAgent('XMPP Bot')
        return bb.goOffline()

    def bbGetTrades(self, user, api_key, **kwargs):
        bb = pybitbargain.BitBargain(user, api_key)
        bb.setUserAgent('XMPP Bot')
        return bb.getTrades(**kwargs)

    def bbCheckTrades(self, addr):
        trades = self.bbGetTrades(self.users[addr]['user'], self.users[addr]['api_key'], active=1)
        active_trades = []
        for trade in trades['response']:
            active_trades.append(trade['pub_id'])
            if trade['pub_id'] not in self.users[addr]['seen_trades']:
                self.send_message(mto=addr, mbody='%s wants to buy %s %s for £%s (£%s each) via %s - %s' % (trade['buyer'], rmZeros(trade['amount']), trade['thing'], rmZeros(trade['price']), rmZeros(trade['price_unit']), trade['pay_method'], trade['url']))
                self.users[addr]['seen_trades'].append(trade['pub_id'])

        for trade in self.users[addr]['seen_trades']:
            if trade not in active_trades:
                self.users[addr]['seen_trades'].remove(trade)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XMPP Bot for BitBargain")
    parser.add_argument('XMPP_User', type=str)
    parser.add_argument('XMPP_Pass', type=str)
    parser.add_argument('--server', type=str)
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    
    xmpp = BitBargainBot(args.XMPP_User, args.XMPP_Pass)
    if args.server != None:
        port = args.port
        if port == None:
            port = 5222
        xmpp.connect((args.server, port))
    else:
        xmpp.connect()

    xmpp.process(block=False)

    while True:
        time.sleep(UPDATE_TIME)
        xmpp.bbPoll()
