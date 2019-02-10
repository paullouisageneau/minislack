
import sys
import os

from .client import Client


def main():
    try:
        token = os.environ.get('SLACK_API_TOKEN')
        if not token:
            raise Exception("The environment variable SLACK_API_TOKEN is not set")
        client = Client(token)
        client.run()
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(e)

    return 1


if __name__ == '__main__':
    sys.exit(main())
