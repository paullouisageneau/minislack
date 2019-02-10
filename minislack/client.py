
import time
import re

from slackclient import SlackClient
from .interface import Interface

RTM_READ_DELAY = 200


class Client:
    def __init__(self, token):
        self.interface = Interface(lambda c, m: self.send(c, m))
        self.connect(token)
        self.last_send_channel = "?"

    def connect(self, token):
        self.sc = SlackClient(token)
        auth = self.sc.api_call('auth.test')
        self.user_id = auth['user_id'] if 'user_id' in auth else None
        if not self.user_id:
            raise Exception('Unable to authenticate to Slack service')
        if not self.sc.rtm_connect(auto_reconnect=True):
            raise Exception("Unable to connect to Slack RTM service")

    def run(self):
        self.interface.start()
        try:
            while self.sc.server.connected:
                time.sleep(RTM_READ_DELAY/1000)
                for event in self.sc.rtm_read():
                    if 'type' not in event:
                        continue
                    event_type = event['type']
                    if event_type == 'message':
                        if 'text' in event and 'channel' in event:
                            text = self.process_text(event['text'])
                            channel = self.resolve_channel(event['channel'])
                            user = self.resolve_user(event['user']) if 'user' in event else None
                            message = "{}: {}".format(user, text) if user else text
                            self.interface.recv(channel, message)
                    elif event_type == 'error':
                        if 'error' in event:
                            error = event['error']
                            msg = error.get('msg', None)
                            message = message = "!error" + (": {}".format(msg) if msg else "")
                            self.interface.recv(self.last_send_channel, message)
        finally:
            self.interface.stop()

    def process_text(self, text):

        def format_user(user_id):
            return ('!' if user_id == self.user_id else '@') + self.resolve_user(user_id)

        def format_channel(channel_id):
            return '#' + self.resolve_channel(channel_id)

        # User
        text = re.sub('<@(\\S+)>', lambda m: format_user(m.group(1)), text)
        # Channel
        text = re.sub('<#(\\S+)>', lambda m: format_channel(m.group(1)), text)
        # Command
        text = re.sub('<!(\\S+)(?:\\|(\\S+))?>', lambda m: '!' + m.group(2), text)
        # With label
        text = re.sub('<(\\S+)\\|(\\S+)>', lambda m: m.group(2), text)
        # Other (URL, etc)
        text = re.sub('<(\\S+)>', lambda m: m.group(1), text)
        # Unescape characters
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text

    def send(self, channel, text):
        user = self.resolve_user(self.user_id)
        message = "{}: {}".format(user, text) if user else text
        # Escape characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        # Send
        self.sc.rtm_send_message(channel, text)
        self.last_send_channel = channel
        # Display
        self.interface.recv(channel, message)

    def resolve_channel(self, channel):
        response = self.sc.api_call('conversations.info', channel=channel)
        if not response['ok']:
            return channel
        info = response['channel']
        if not info.get('is_channel', False) and not info.get('is_group', False):
            return channel
        if info.get('is_mpim', False):
            return channel
        return info.get('name_normalized', channel)

    def resolve_user(self, user):
        response = self.sc.api_call('users.info', user=user)
        if not response['ok']:
            return user
        info = response['user']
        name = info['profile'].get('display_name_normalized', '')
        if name:
            return name
        name = info['profile'].get('real_name_normalized', '')
        if name:
            return name
        return user
