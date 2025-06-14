import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate

logger = logging.getLogger('authentication_logger')
handler = logging.FileHandler('authentication.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class Command(BaseCommand):
    help = 'Authenticate a user with username and password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for authentication')
        parser.add_argument('password', type=str, help='Password for authentication')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            logger.info(f"Login success for username: {username}")
            self.stdout.write(self.style.SUCCESS('Auth-Type := Accept'))
            exit(0)  # Exit with status 0 for success
        else:
            logger.warning(f"Login failed for username: {username}")
            self.stdout.write(self.style.ERROR('Auth-Type := Reject'))
            exit(1)  # Exit with status 1 for failure