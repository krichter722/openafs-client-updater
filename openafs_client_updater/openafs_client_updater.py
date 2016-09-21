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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_stdout_handler = logging.StreamHandler()
logger_stdout_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s:%(message)s')
logger_stdout_handler.setFormatter(logger_formatter)
logger.addHandler(logger_stdout_handler)

@plac.annotations(hostname=("The hostname to base the query on", "positional"),
    foreground=("A flag indicating that the process ought to run in the foreground instead of being forked (ignored if oneshot is specified)", "flag"),
    oneshot=("A flag indicating that the process ought not run in a loop, but exit after one run", "flag"),
    interval=("The interval in seconds between two check (ignored if oneshot is specified)", "option"),
)
def openafs_client_updater(hostname="richtercloud.de", foreground=False, oneshot=False, interval=2*60, log_dir="/var/log/openafs-client-updater", log_file_name="openafs-client-updater.log"):
    print (log_dir)
    if not os.path.exists(log_dir):
        logger.debug("Creating inexisting log directory '%s'" % (log_dir,))
        os.makedirs(log_dir)
    elif not os.path.isdir(log_dir):
        raise ValueError("log directory '%s' exists, but is not directory" % (log_dir,))
    logger_file_handler = logging.FileHandler(filename=os.path.join(log_dir, log_file_name), mode='a', encoding=None, delay=False)
    logger_file_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)

    def __check__():
        ip = socket.gethostbyname(hostname)
        cellservdb_file_path = "/etc/openafs/CellServDB"
        cellservdb_file = open(cellservdb_file_path, "r")
        cellservdb_file_lines = cellservdb_file.readlines()
        cellservdb_dict = parse_cellservdb_file(cellservdb_file_lines)
        if not hostname in cellservdb_dict:
            raise ValueError("The hostname '%s' isn't present in CellServDB '%s'" % (hostname, cellservdb_file_path))
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
    main()