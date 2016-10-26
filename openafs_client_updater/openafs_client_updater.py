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

import plac
import subprocess as sp
import socket
import re
import logging
import time
import os
import configparser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_stdout_handler = logging.StreamHandler()
logger_stdout_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s:%(message)s')
logger_stdout_handler.setFormatter(logger_formatter)
logger.addHandler(logger_stdout_handler)

ip_service_dig = "dig"
ip_service_ipecho = "ipecho"
ip_service_default = ip_service_dig

# binaries
systemctl = "systemctl"

__ip_service_docstring__ = "Whether to use DNS name resolution or an external IP echo service to detect changes to DDNS IP. The choice impacts the shortness of intervals (DNS queries can performed more frequently than IP echo service queries because you get blocked for the latter if requests are sent too often) and the possibility to have a LAN (you might want to resolve a server name to a LAN IP inside the LAN rather than its WAN IP, i.e. you need an IP echo service)"

@plac.annotations(hostname=("The hostname to base the query on", "positional"),
    foreground=("A flag indicating that the process ought to run in the foreground instead of being forked (ignored if oneshot is specified)", "flag"),
    oneshot=("A flag indicating that the process ought not run in a loop, but exit after one run", "flag"),
    interval=("The interval in seconds between two check (ignored if oneshot is specified)", "option"),
    ip_service=(__ip_service_docstring__, "option"),
)
def openafs_client_updater(hostname=None,
    foreground=False,
    oneshot=False,
    interval=2*60,
    log_dir="/var/log/openafs-client-updater",
    log_file_name="openafs-client-updater.log",
    config_file_path="/etc/openafs-client-updater.conf",
    ip_service=ip_service_default):
    if not os.path.exists(log_dir):
        logger.debug("Creating inexisting log directory '%s'" % (log_dir,))
        os.makedirs(log_dir)
    elif not os.path.isdir(log_dir):
        raise ValueError("log directory '%s' exists, but is not directory" % (log_dir,))
    logger_file_handler = logging.FileHandler(filename=os.path.join(log_dir, log_file_name), mode='a', encoding=None, delay=False)
    logger_file_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)
    if hostname is None:
        logger.debug("reading hostname from configuration file '%s'" % (config_file_path,))
        config = configparser.ConfigParser(allow_no_value=True)
        if not os.path.exists(config_file_path):
            raise RuntimeError("configuration file '%s' doesn't exist and hostname isn't specified on command line, can't proceed" % (config_file_path,))
        config.read(config_file_path)
        hostnames = config.items("hostnames")
        if len(hostnames) > 1:
            raise ValueError("more than one hostname isn't supported (yet)")
        hostname = hostnames[0][0] # `configparser.ConfigParser.items` returns a list of tuples with key and value
        logger.debug("hostname is '%s'" % (hostname,))
    def __check__():
        if ip_service == ip_service_dig:
            logger.debug("checking external IP with DNS resolution")
            ip = socket.gethostbyname(hostname)
        elif ip_service == ip_service_ipecho:
            echo_url = "http://ipecho.net/plain"
            logger.debug("checking external IP at '%s'" % (echo_url,))
            dyndns_response = urllib2.urlopen(echo_url).readline().strip()
            ip = dyndns_response
        else:
            raise ValueError("IP service '%s' not supported" % (ip_service,))
        cellservdb_file_path = "/etc/openafs/CellServDB"
        cellservdb_file = open(cellservdb_file_path, "r")
        cellservdb_file_lines = cellservdb_file.readlines()
        cellservdb_dict = parse_cellservdb_file(cellservdb_file_lines)
        if not hostname in cellservdb_dict:
            raise ValueError("The hostname '%s' isn't present in CellServDB '%s'" % (hostname, cellservdb_file_path))
        if len(cellservdb_dict[hostname]) > 5:
            # avoid `Too many hosts for cell [cell] in configuration file /etc/openafs/CellServDB` (maximum of entries unclear, must doesn't need to be specified)
            cellservdb_dict[hostname] = []
        if not ip in cellservdb_dict[hostname]:
            cellservdb_dict[hostname].append(ip)
            logger.info("adding missing IP '%s'" % (ip,))
            # only need to write back if an IP was missing
            cellservdb_file_lines = create_cellservdb_lines(cellservdb_dict)
            cellservdb_file.close()
            cellservdb_file = open(cellservdb_file_path, "w")
            cellservdb_file.writelines(cellservdb_file_lines)
            cellservdb_file.flush()
            cellservdb_file.close()
            system_unit_name = "openafs-client.service"
            logger.info("restarting OpenAFS client systemd unit '%s'" % (system_unit_name,))
            # it's not sufficient to run `systemctl restart`, but necessary to run separate stop and start actions (most likely a bug)
            sp.check_call([systemctl, "stop", system_unit_name])
            sp.check_call([systemctl, "start", system_unit_name])
    if oneshot:
        __check__()
        return
    def __loop__():
        while True:
            __check__()
            time.sleep(interval)
    if not foreground:
        pid = os.fork()
        if pid == 0:
            __loop__()
        # don't care about parent
        sys.exit(0)
    else:
        __loop__()

def create_cellservdb_lines(cellservdb_dict):
    """(Re-)creates lines for CellServDB file to be written with
    `file.writelines` (including necessary newline characters"""
    ret_value = []
    for hostname in cellservdb_dict:
        ret_value.append(">%s #%s\n" % (hostname, hostname))
        for ip in cellservdb_dict[hostname]:
            ret_value.append("%s #%s\n" % (ip, hostname))
    return ret_value

def parse_cellservdb_file(cellservdb_file_lines):
    """Creates and returns a dict mapping hostnames to IPs."""
    ret_value = dict()
    hostname = None
    for line in cellservdb_file_lines:
        match = re.search(">[\\W]*(?P<host>[\\w\\.]+)[\\W]+", line)
        if match != None:
            hostname = match.group("host")
            logger.debug("found hostname '%s'" % (hostname,))
        match = re.search("[\\W]*(?P<ip>[0-9\\.]+)[\\W]+", line)
        if match != None:
            ip = match.group("ip")
            logger.debug("found IP '%s' for hostname '%s'" % (ip, hostname))
            if not hostname in ret_value or ret_value[hostname] is None:
                ret_value[hostname] = []
            ret_value[hostname].append(ip)
    return ret_value

def main():
    """For setuptools entry_point."""
    plac.call(openafs_client_updater)

if __name__ == "__main__":
    try:
        main()
    except:
        logger.exception()
