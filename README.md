minislack
=========

A mini terminal client for [Slack](https://slack.com)

It shows what happens in the different channels on a single interleaved feed and allows you to post. Otherwise, it is as limited as it gets.

Setup
-----

Install the dependency [python-slackclient](https://github.com/slackapi/python-slackclient).

Usage
-----

1. Get a Slack token for the workspace [here](https://api.slack.com/custom-integrations/legacy-tokens).

2. Export the token as an environment variable and run the client.

```bash
$ export SLACK_API_TOKEN="xoxp-XXXX"
$ cd minislack
$ ./run.py
```

