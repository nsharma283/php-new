# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""AppDynamics Extension

Downloads, installs and configures the AppDynamics agent for PHP
"""
import os
import os.path
import logging


_log = logging.getLogger('appdynamics')


DEFAULTS = {
    'APPDYNAMICS_HOST': 's3-us-west-2.amazonaws.com/niksappd',
    'APPDYNAMICS_VERSION': '4.1.1.0',
    'APPDYNAMICS_PACKAGE': 'appdynamics-php-agent-x64-linux-{APPDYNAMICS_VERSION}.tar.gz',
    'APPDYNAMICS_DOWNLOAD_URL': 'https://{APPDYNAMICS_HOST}/php_agent/'
                             'archive/{APPDYNAMICS_VERSION}/{APPDYNAMICS_PACKAGE}',
}


class AppDynamicsInstaller(object):
    def __init__(self, ctx):
        self._log = _log
        self._ctx = ctx
        self._detected = False
        self.app_name = None
        self.account_access_key = None
        try:
            self._log.info("Initializing")
            if ctx['PHP_VM'] == 'php':
                self._merge_defaults()
                self._load_service_info()
                self._load_php_info()
                self._load_appdynamics_info()
        except Exception:
            self._log.exception("Error installing AppDynamics! "
                                "AppDynamics will not be available.")

    def _merge_defaults(self):
        for key, val in DEFAULTS.iteritems():
            if key not in self._ctx:
                self._ctx[key] = val

    def _load_service_info(self):
        self._log.info("Loading AppDynamics service info.")
        services = self._ctx.get('VCAP_SERVICES', {})
        service_defs = services.get('appdynamics', [])
        if len(service_defs) == 0:
            self._log.info("AppDynamics services with tag appdynamics not detected.")
            self._log.info("Looking for tag app-dynamics service.")
            service_defs = services.get('app-dynamics', [])
            if len(service_defs) == 0:
               self._log.info("AppDynamics services with tag app-dynamics not detected.")
               self._log.info("Looking for Appdynamics user-provided service.")
               service_defs = services.get('user-provided', [])
               if len(service_defs) == 0:
                   self._log.info("AppDynamics services not detected.")
        if len(service_defs) > 1:
            self._log.warn("Multiple AppDynamics services found, "
                           "credentials from first one.")
        if len(service_defs) > 0:
            service = service_defs[0]
            creds = service.get('credentials', {})
            self.account_access_key = creds.get('account-access-key', None)
            if self.account_access_key:
                self._log.debug("AppDynamics service detected.")
                self._detected = True

    def _load_appdynamics_info(self):
        vcap_app = self._ctx.get('VCAP_APPLICATION', {})
        self.app_name = vcap_app.get('name', None)
        self._log.debug("App Name [%s]", self.app_name)

        if 'APPDYNAMICS_LICENSE' in self._ctx.keys():
            if self._detected:
                self._log.warn("Detected a AppDynamics Service & Manual Key,"
                               " using the manual key.")
            self.license_key = self._ctx['APPDYNAMICS_LICENSE']
            self._detected = True

        if self._detected:
            appdynamics_so_name = 'appdynamics-%s%s.so' % (
                self._php_api, (self._php_zts and 'zts' or ''))
            self.appdynamics_so = os.path.join('@{HOME}', 'appdynamics',
                                            'agent', self._php_arch,
                                            appdynamics_so_name)
            self._log.debug("PHP Extension [%s]", self.appdynamics_so)
            self.log_path = os.path.join('@{HOME}', 'logs',
                                         'appdynamics-daemon.log')
            self._log.debug("Log Path [%s]", self.log_path)
            self.daemon_path = os.path.join(
                '@{HOME}', 'appdynamics', 'daemon',
                'appdynamics-daemon.%s' % self._php_arch)
            self._log.debug("Daemon [%s]", self.daemon_path)
            self.socket_path = os.path.join('@{HOME}', 'appdynamics',
                                            'daemon.sock')
            self._log.debug("Socket [%s]", self.socket_path)
            self.pid_path = os.path.join('@{HOME}', 'appdynamics',
                                         'daemon.pid')
            self._log.debug("Pid File [%s]", self.pid_path)

    def _load_php_info(self):
        self.php_ini_path = os.path.join(self._ctx['BUILD_DIR'],
                                         'php', 'etc', 'php.ini')
        self._php_extn_dir = self._find_php_extn_dir()
        self._php_api, self._php_zts = self._parse_php_api()
        self._php_arch = self._ctx.get('APPDYNAMICS_ARCH', 'x64')
        self._log.debug("PHP API [%s] Arch [%s]",
                        self._php_api, self._php_arch)

    def _find_php_extn_dir(self):
        with open(self.php_ini_path, 'rt') as php_ini:
            for line in php_ini.readlines():
                if line.startswith('extension_dir'):
                    (key, val) = line.strip().split(' = ')
                    return val.strip('"')

    def _parse_php_api(self):
        tmp = os.path.basename(self._php_extn_dir)
        php_api = tmp.split('-')[-1]
        php_zts = (tmp.find('non-zts') == -1)
        return php_api, php_zts

    def should_install(self):
        return self._detected

    def modify_php_ini(self):
#        with open(self.php_ini_path, 'rt') as php_ini:
#            lines = php_ini.readlines()
#        extns = [line for line in lines if line.startswith('extension=')]
#        if len(extns) > 0:
#            pos = lines.index(extns[-1]) + 1
#        else:
#            pos = lines.index('#{PHP_EXTENSIONS}\n') + 1
#        lines.insert(pos, 'extension=%s\n' % self.appdynamics_so)
#        lines.append('\n')
#        lines.append('[appdynamics]\n')
#        lines.append('appdynamics.license=%s\n' % self.license_key)
#        lines.append('appdynamics.appname=%s\n' % self.app_name)
#        lines.append('appdynamics.daemon.logfile=%s\n' % self.log_path)
#        lines.append('appdynamics.daemon.location=%s\n' % self.daemon_path)
#        lines.append('appdynamics.daemon.port=%s\n' % self.socket_path)
#        lines.append('appdynamics.daemon.pidfile=%s\n' % self.pid_path)
#        with open(self.php_ini_path, 'wt') as php_ini:
#            for line in lines:
#                php_ini.write(line)

    	exit_code = os.system("echo calling out env; env")
    	exit_code = os.system("echo ${VCAP_APPLICATION} |  sed -e 's/.*instance_id\":\"//g;s/,\"host.*//g;s/\",.*\"//g'")
    	exit_code = os.system("echo $HOSTNAME")
    	exit_code = os.system("ps -auxw; cd /home/vcap; chmod -R 755 ./app; chmod 777 ./app/appdynamics/logs; export APP_HOSTNAME=`echo $VCAP_APPLICATION | sed -e 's/.*instance_id\":\"//g;s/,\"host.*//g;s/\",.*\"//g'`; export APP_TIERNAME=`echo $VCAP_APPLICATION | sed -e 's/.*application_name.:.//g;s/\".*application_uri.*//g' `; PATH=$PATH:./app/php/bin/ ./app/appdynamics/install.sh -s -i ./app/appdynamics/phpini -a=appdynamics@bb6604c1-fbe0-400a-a76b-87c26254fe5e 54.245.245.19 443 php-machineagentPCF $APP_TIERNAME $APP_HOSTNAME")
    	exit_code = os.system("echo sleep 5; sleep 5; ps -auxw; php -i")
    	exit_code = os.system("echo adding to phpini; cat /home/vcap/app/appdynamics/phpini/appdynamics_agent.ini >> /home/vcap/app/php/etc/php.ini")

# Extension Methods
def preprocess_commands(ctx):
    exit_code = os.system("echo !!! preprocess_commands")
    exit_code = os.system("pwd; ls -al; env ; echo VCAP_APPLICATION; echo ${VCAP_APPLICATION} |  sed -e 's/.*instance_id\":\"//g;s/,\"host.*//g;s/\",.*\"//g'") 
    ctx.put("ADDITIONAL_PREPROCESS_CMDS","env")
    return ()

def service_commands(ctx):
    exit_code = os.system("echo !!!! service_commands")
    exit_code = os.system("pwd; ls -al; env ; echo VCAP_APPLICATION; echo ${VCAP_APPLICATION} |  sed -e 's/.*instance_id\":\"//g;s/,\"host.*//g;s/\",.*\"//g'") 
    return {}


def service_environment(ctx):
    exit_code = os.system("echo !!!! service_environment")
    exit_code = os.system("pwd; ls -al; env ;echo VCAP_APPLICATION; echo ${VCAP_APPLICATION} |  sed -e 's/.*instance_id\":\"//g;s/,\"host.*//g;s/\",.*\"//g'") 
    return {}


def compile(install):
    exit_code = os.system("echo !!!! compile ")
    appdynamics = AppDynamicsInstaller(install.builder._ctx)
    if appdynamics.should_install():
        _log.info("Installing AppDynamics")
        install.package('APPDYNAMICS')
        _log.info("Configuring AppDynamics in php.ini")
        appdynamics.modify_php_ini()
        _log.info("AppDynamics Installed.")
    return 0
