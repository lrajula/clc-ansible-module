#!/usr/bin/python



import clc_ansible_module.clc_firewall as clc_firewall
from clc_ansible_module.clc_firewall import ClcFirewall

import clc as clc_sdk
from clc import CLCException
import mock
from mock import patch
from mock import create_autospec
import unittest

class TestClcFirewall(unittest.TestCase):

    def setUp(self):
        self.clc = mock.MagicMock()
        self.module = mock.MagicMock()
        self.datacenter=mock.MagicMock()

    def test_clc_set_credentials_w_creds(self):
        with patch.dict('os.environ', {'CLC_V2_API_USERNAME': 'hansolo', 'CLC_V2_API_PASSWD': 'falcon'}):
            with patch.object(clc_firewall, 'clc_sdk') as mock_clc_sdk:
                under_test = ClcFirewall(self.module)
                under_test._set_clc_credentials_from_env()

        mock_clc_sdk.v2.SetCredentials.assert_called_once_with(
            api_username='hansolo',
            api_passwd='falcon')

    def test_get_firewall_policy_fail(self):
        source_account_alias = 'WFAD'
        location = 'VA1'
        firewall_policy = 'fake_policy'


        mock_policy = mock.MagicMock()
        # mock_policy.return_value =
        test_firewall_policy = ClcFirewall(self.module)
        test_firewall_policy._get_firewall_policy(source_account_alias, location, firewall_policy)
        self.assertTrue(self.module.fail_json.called)

    def test_get_firewall_policy_pass(self):
        source_account_alias = 'WFAD'
        location = 'wa1'
        firewall_policy = '4d6e52d872754e12a71d672b2b50ec19'


        test_firewall_policy = ClcFirewall(self.module)
        test_firewall_policy._get_firewall_policy(source_account_alias, location, firewall_policy)
        self.assertFalse(self.module.fail_json.called)


    def test_get_firewall_policy_list_fail(self):
        source_account_alias = 'WFAD'
        location = 'VA1'

        mock_policy = mock.MagicMock()
        # mock_policy.return_value =
        test_firewall_policy = ClcFirewall(self.module)
        test_firewall_policy._get_firewall_policy_list(source_account_alias, location)
        self.assertTrue(self.module.fail_json.called)

    def test_get_firewall_policy_list_pass_w_destination(self):
        pass

    def test_get_firewall_policy_list_pass_wo_destination(self):
        pass

    def test_create_firewall_policy(self):
        pass

    def test_delete_firewall_policy(self):
        pass

    def test_firewall_policy_exists(self):
        pass

    def test_ensure_firewall_policy_absent(self):
        pass

    def test_ensure_firewall_policy_present(self):
        pass

    def test_main(self):
        pass

    def test_firewall_policy_does_not_exist(self):
        pass


if __name__ == '__main__':
    unittest.main()
