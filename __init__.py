import time
from email_processor import main

if __name__ == '__main__':
    while True:
        refresh = main()
        time.sleep(refresh)
