"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""

import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman
from datetime import date

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""

        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""

        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""

        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""

        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    def _assert_that_accounts_are_the_same(self, a, b):
        self.assertEqual(a["name"], b.name)
        self.assertEqual(a["email"], b.email)
        self.assertEqual(a["address"], b.address)
        self.assertEqual(a["phone_number"], b.phone_number)
        self.assertEqual(a["date_joined"], str(b.date_joined))

    def _get_accounts_url(self, id):
        if id is None:
            return BASE_URL

        return '{base}/{id}'.format(base=BASE_URL, id=id)

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""

        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""

        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""

        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""

        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""

        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_read_an_account(self):
        """Reading an account should show the information of a specified account"""

        account = self._create_accounts(1)[0]
        url = self._get_accounts_url(account.id)

        response = self.client.get(url)

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure the account information is correct
        retrieved = response.get_json()
        self._assert_that_accounts_are_the_same(retrieved, account)

    def test_read_a_nonexisting_account(self):
        """Reading an account that does not exist should return a 404 error"""

        response = self.client.get(
            '{base}/{id}'.format(base=BASE_URL, id=0),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_account(self):
        """Updating an account should persist the new information"""

        account = self._create_accounts(1)[0]
        account.name = 'UpdateTest'
        account.phone_number = '000-000'

        url = self._get_accounts_url(account.id)

        response = self.client.put(
            url,
            json=account.serialize(),
            content_type="application/json"
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure the account information is correct
        test = self.client.get(url)
        retrieved = test.get_json()
        self._assert_that_accounts_are_the_same(retrieved, account)

    def test_update_non_existing_account(self):
        """Updating an account that does not exist should return a 404 error"""

        account = self._create_accounts(1)[0]
        account.name = 'UpdateTest'

        url = self._get_accounts_url(0)

        response = self.client.put(
            url,
            json=account.serialize(),
            content_type="application/json"
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """Deleting an account should remove the account from the system"""

        account = self._create_accounts(1)[0]

        url = self._get_accounts_url(account.id)

        response = self.client.delete(url)

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Make sure the account is no longer in the system.
        test = self.client.get(url)
        self.assertEqual(test.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_existing_account(self):
        """Deleting an account that does not exist should also return a 204 status"""

        url = self._get_accounts_url(0)

        response = self.client.delete(url)

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_accounts(self):
        """It should retrieve a list of all accounts in the system."""

        count = 5
        self._create_accounts(count)

        url = self._get_accounts_url(None)
        response = self.client.get(url)

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure that all the accounts are there.
        retrieved = response.get_json()
        self.assertEqual(len(retrieved), count)

    def test_list_accounts_if_no_accounts_found(self):
        """It should respond with an empty list and a 200 status code."""

        url = self._get_accounts_url(None)

        response = self.client.get(url)

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure that all the accounts are there.
        retrieved = response.get_json()
        self.assertEqual(len(retrieved), 0)

    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""

        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ######################################################################
    #  S E C U R I T Y   T E S T   C A S E S
    ######################################################################

    def test_force_to_https(self):
        """A request should respond with the correct security headers"""

        resp = self.client.get('/', environ_overrides=HTTPS_ENVIRON)

        # Debugging: Afișează toate header-ele
        print("Response headers:", resp.headers)

        required_headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

        for header, value in required_headers.items():
            self.assertEqual(resp.headers.get(header), value)

    def test_for_cors_headers(self):
        """A request should respond with the correct CORS headers"""

        resp = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(resp.headers.get('Access-Control-Allow-Origin'), '*')

    def test_for_account_to_string(self):
        """Account repr should return the account name and id"""

        account = self._create_accounts(1)[0]

        string_test = account.__repr__()

        self.assertEqual(string_test, '<Account {name} id=[{id}]>'.format(name=account.name, id=account.id))

    def test_for_account_with_no_date_joined(self):
        """Deserialize with no date joined value makes date joined today"""

        account = self._create_accounts(1)[0]
        serial = account.serialize()
        serial['date_joined'] = None

        account.deserialize(serial)

        self.assertEqual(account.date_joined, date.today())

