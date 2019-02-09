
import sys

from .client import Client


def main():
    try:
        client = Client()
        client.run()
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(e)

    return 1


if __name__ == '__main__':
    sys.exit(main())
