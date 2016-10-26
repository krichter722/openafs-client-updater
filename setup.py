#!/usr/bin/python
# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    Dieses Programm ist Freie Software: Sie können es unter den Bedingungen
#    der GNU General Public License, wie von der Free Software Foundation,
#    Version 3 der Lizenz oder (nach Ihrer Wahl) jeder neueren
#    veröffentlichten Version, weiterverbreiten und/oder modifizieren.
#
#    Dieses Programm wird in der Hoffnung, dass es nützlich sein wird, aber
#    OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
#    Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
#    Siehe die GNU General Public License für weitere Details.
#
#    Sie sollten eine Kopie der GNU General Public License zusammen mit diesem
#    Programm erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from setuptools import setup, find_packages, Command
from  setuptools.command.install  import  install
from pkg_resources import parse_version
import openafs_client_updater.openafs_client_updater_globals as openafs_client_updater_globals
import subprocess as sp
import shutil
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

# binaries
systemctl = "systemctl"

class SystemdServiceInstallCommand(Command):
    """setuptools Command"""
    description = "Create a systemd unit"
    user_options = []

    def initialize_options(self):
        """init options"""
        pass

    def finalize_options(self):
        """finalize options"""
        pass

    def run(self):
        """runner"""
        logger.debug("running systemd service installation post-install hook")
        systemd_service_install()

def systemd_service_install():
    systemd_unit_name = openafs_client_updater_globals.app_name

    # @TODO: adjust to deal with setuptools options
    systemd_service_file_path = "/lib/systemd/system/%s.service" % (systemd_unit_name,)

    sp.call([systemctl, "stop", systemd_unit_name]) # might fail if service doesn't exist
    shutil.copy2("%s.service" % (systemd_unit_name,), "/lib/systemd/system/%s.service" % (systemd_unit_name,))
    sp.check_call([systemctl, "daemon-reload"])
    sp.check_call([systemctl, "start", systemd_unit_name])

setup(
    name = openafs_client_updater_globals.app_name,
    version_command = ("git describe --tags", "pep440-git-local"),
    packages = find_packages(),
    setup_requires = ["setuptools-version-command"],
    install_requires = ["plac>=0.9.1", "configparser"],
    entry_points={
        'console_scripts': [
            '%s = openafs_client_updater.openafs_client_updater:main' % (openafs_client_updater_globals.app_name, ),
        ],
    },
    cmdclass = {'systemd_service':SystemdServiceInstallCommand},
    test_suite="tests",
)
