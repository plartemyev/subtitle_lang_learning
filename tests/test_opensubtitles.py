"""OpenSubtitlesClient contract: registered-client User-Agent and login flow.

The XML-RPC endpoint only accepts anonymous logins sent with a registered
client's User-Agent (Vlsub); without it the server refuses the session.
"""
import sys
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.opensubtitles import OpenSubtitlesClient

REGISTERED_UA = 'VLsub 0.10.2'


class ClientConfigTest(unittest.TestCase):
    def test_registered_user_agent_is_used_on_the_transport(self):
        client = OpenSubtitlesClient()
        self.assertEqual(client.ua, REGISTERED_UA)
        self.assertEqual(client.xmlrpc_transport.user_agent, REGISTERED_UA)


class LoginTest(unittest.TestCase):
    def test_login_passes_registered_ua_and_stores_token(self):
        client = OpenSubtitlesClient()
        with unittest.mock.patch.object(client, 'xmlrpc') as proxy:
            proxy.LogIn.return_value = {'status': '200 OK', 'token': 'tok-1'}
            client.login('', '')
        proxy.LogIn.assert_called_once_with('', '', 'en', REGISTERED_UA)
        self.assertEqual(client.token, 'tok-1')

    def test_login_failure_raises_and_leaves_no_token(self):
        client = OpenSubtitlesClient()
        with unittest.mock.patch.object(client, 'xmlrpc') as proxy:
            proxy.LogIn.return_value = {'status': '401 Unauthorized'}
            with self.assertRaises(Exception):
                client.login('', '')
        self.assertIsNone(client.token)


if __name__ == '__main__':
    unittest.main()
