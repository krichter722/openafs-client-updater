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

import unittest
import openafs_client_updater.openafs_client_updater as openafs_client_updater

class OpenafsClientUpdaterTest(unittest.TestCase):

    def test_parse_cellservdb_file(self):
        test_file_path = "tests/CellServDB"
        test_file = open(test_file_path, "r")
        test_file_lines = test_file.readlines()
        result = openafs_client_updater.parse_cellservdb_file(test_file_lines)
        exp_result = {"richtercloud.de": ["192.168.179.1", "94.223.92.236", "88.75.17.58"]}
        self.assertEqual(result, exp_result)

    def test_parse_cellservdb_file(self):
        result = openafs_client_updater.create_cellservdb_lines({"host.name": ["1.2.3.4", "2.3.4.5", "3.4.5.6"]})
        exp_result = [">host.name #host.name\n", "1.2.3.4 #host.name\n", "2.3.4.5 #host.name\n", "3.4.5.6 #host.name\n"]
        self.assertEqual(result, exp_result)

if __name__ == '__main__':
    unittest.main()
