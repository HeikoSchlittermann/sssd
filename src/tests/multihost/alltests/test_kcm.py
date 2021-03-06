"""
Automation of kcm related bugs
"""

from __future__ import print_function
import re
import pytest
import time
import paramiko
import subprocess
from sssd.testlib.common.expect import pexpect_ssh
from sssd.testlib.common.exceptions import SSHLoginException
from sssd.testlib.common.utils import sssdTools, LdapOperations
from constants import ds_instance_name


@pytest.mark.usefixtures('setup_sssd', 'create_posix_usersgroups')
@pytest.mark.kcm
class TestKcm(object):
    """
    This is for kcm bugs automation
    """
    @pytest.mark.tier1_2
    def test_client_timeout(self, multihost, backupsssdconf):
        """
        :Title: kcm: Increase client idle
        timeout to 5 minutes

        @bugzilla:
        https://bugzilla.redhat.com/show_bug.cgi?id=1884205
        """
        client = sssdTools(multihost.client[0])
        domain_params = {'debug_level': '9'}
        client.sssd_conf('kcm', domain_params)
        multihost.client[0].service_sssd('restart')
        user = 'foo1@example1'
        client = pexpect_ssh(multihost.client[0].sys_hostname, user,
                             'Secret123', debug=False)
        client.login(login_timeout=30, sync_multiplier=5,
                     auto_prompt_reset=False)
        sssdTools(multihost.client[0]).clear_sssd_cache()
        multihost.client[0].run_command("systemctl restart sssd-kcm")
        multihost.client[0].run_command("> /var/log/sssd/sssd_kcm.log")
        start_time = time.time()
        multihost.client[0].run_command("kinit foo1 <&- & ")
        end_time = time.time()
        client.logout()
        assert end_time - start_time >= 300
        grep_cmd = multihost.client[0].run_command("grep"
                                                   " 'Terminated"
                                                   " client'"
                                                   " /var/log/sssd/"
                                                   "sssd_kcm.log")
        assert 'Terminated client' in grep_cmd.stdout_text

    @pytest.mark.tier1_2
    def test_refresh_contain_timestamp(self,
                                       multihost,
                                       backupsssdconf):
        """
        :title: kcm: First smart refresh query contains
         modifyTimestamp even if the modifyTimestamp is 0
        :bugzilla: https://bugzilla.redhat.com/show_bug.cgi?id=1926454
        :customerscenario: true
        :id: 09f654c4-759d-11eb-bfff-002b677efe14
        :steps:
          1. Configure SSSD with sudo
          2. Leave ou=sudoers empty - do not define any rules
          3. See that smart refresh does not contain
          modifyTimestamp in the filter
        :expectedresults:
          1. Should succeed
          2. Should succeed
          3. Should succeed
        """
        tools = sssdTools(multihost.client[0])
        ldap_params = {'domains': 'example1'}
        tools.sssd_conf('sssd', ldap_params)
        ldap_params = {'sudo_provider': 'ldap',
                       'ldap_sudo_smart_refresh_interval': '60'}
        tools.sssd_conf('domain/%s' % (ds_instance_name), ldap_params)
        multihost.client[0].service_sssd('restart')
        multihost.client[0].run_command("> /var/log/sssd/sssd_example1.log")
        time.sleep(65)
        log_location = "/var/log/sssd/sssd_example1.log"
        grep_cmd = multihost.client[0].run_command(f"grep "
                                                   f"'calling "
                                                   f"ldap_search_ext with' "
                                                   f"{log_location}")
        assert 'modifyTimestamp>=' not in grep_cmd.stdout_text
