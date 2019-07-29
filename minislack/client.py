
import re
import slack

from .interface import Interface

TIMEOUT = 60


class Client:
    def __init__(self, token):
        self.interface = Interface(lambda c, m: self.send(c, m))
        self.connect(token)
        self.last_send_channel = "?"

    def connect(self, token):
        webc = slack.WebClient(token=token)
        auth = webc.api_call('auth.test')
        self.user_id = auth['user_id']
        if not self.user_id:
            raise Exception('Unable to authenticate to Slack service')

        slack.RTMClient.on(event='message', callback=self.on_message)
        slack.RTMClient.on(event='error', callback=self.on_error)
        self.rtmc = slack.RTMClient(token=token, timeout=TIMEOUT)
        self.webc = slack.WebClient(token=token, timeout=TIMEOUT)

    def run(self):
        self.interface.start()
        try:
            self.rtmc.start()
        finally:
            self.interface.stop()

    def on_message(self, **payload):
        data = payload['data']
        if 'text' in data and 'channel' in data:
            text = self.process_text(data['text'])
            channel = self.resolve_channel(data['channel'])
            user = self.resolve_user(data['user']) if 'user' in data else None
            message = "{}: {}".format(user, text) if user else text
            self.interface.recv(channel, message)

    def on_error(self, **payload):
        data = payload['data']
        if 'error' in data:
            error = data['error']
            msg = error.get('msg', None)
            message = message = "!error" + (": {}".format(msg) if msg else "")
            self.interface.recv(self.last_send_channel, message)

    def process_text(self, text):

        def format_user(user_id):
            return ('!' if user_id == self.user_id else '@') + self.resolve_user(user_id)

        def format_channel(channel_id):
            return '#' + self.resolve_channel(channel_id)

        # User
        text = re.sub('<@([\\S]+)(?:\\|([^<>]+))?>', lambda m: format_user(m.group(1)), text)
        # Channel
        text = re.sub('<#([\\S]+)(?:\\|([^<>]+))?>', lambda m: format_channel(m.group(1)), text)
        # Command
        text = re.sub('<!(?:([^<>]+)\\|)?([^<>]+)>', lambda m: '!' + m.group(2), text)
        # With label
        text = re.sub('<([^<>]+)\\|([^<>]+)>', lambda m: m.group(2), text)
        # Other (non-labeled URL, etc)
        text = re.sub('<([^<>]+)>', lambda m: m.group(1), text)
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
        self.webc.rtm_send_message(channel, text)
        self.last_send_channel = channel
        # Display
        self.interface.recv(channel, message)

    def resolve_channel(self, channel):
        response = self.webc.api_call('conversations.info', params={'channel': channel})
        if not response['ok']:
            return channel
        info = response['channel']
        if not info.get('is_channel', False) and not info.get('is_group', False):
            return channel
        if info.get('is_mpim', False):
            return channel
        return info.get('name_normalized', channel)

    def resolve_user(self, user):
        response = self.webc.api_call('users.info', params={'user': user})
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
