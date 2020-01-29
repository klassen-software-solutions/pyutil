import json.decoder
import socket
import subprocess
import tempfile
import time
import unittest

from contextlib import closing

import requests
import requests.exceptions

import kss.util.jsonreader as jsonreader


def _find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

class JSONReaderTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Start the server, then wait for it to be ready
        cls._port = _find_free_port()
        cls._server = subprocess.Popen("python3 -m http.server %d" % cls._port,
                                       shell=True,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
        while True:
            try:
                requests.get(cls._url("dontcare"))
                break
            except requests.exceptions.ConnectionError:
                time.sleep(0.1)


    @classmethod
    def tearDownClass(cls):
        cls._server.terminate()
        cls._server.wait()


    def test_from_file(self):
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'{"one": 1, "two": 2}\n')
            temp.flush()
            js = jsonreader.from_file(temp.name)
            self.assertEqual(js, {"one": 1, "two": 2})

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'[1, 2, 3, 4]\n')
            temp.flush()
            js = jsonreader.from_file(temp.name)
            self.assertEqual(js, [1, 2, 3, 4])

        with self.assertRaises(FileNotFoundError):
            jsonreader.from_file("/no/such/file.js")

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'this is not a valid JSON file\n')
            temp.flush()
            with self.assertRaises(json.decoder.JSONDecodeError):
                jsonreader.from_file(temp.name)


    def test_from_url(self):
        with self.assertRaises(requests.exceptions.ConnectionError):
            jsonreader.from_url("http://no.such.machine.found/")

        js = jsonreader.from_url(self._url("dictionary.json"))
        self.assertEqual(js, {"one": 1, "two": 2})

        js = jsonreader.from_url(self._url("array.json"))
        self.assertEqual(js, [1, 2, 3, 4])

        with self.assertRaises(jsonreader.NotOkResponseError):
            jsonreader.from_url(self._url("not_there.json"))

        with self.assertRaises(json.decoder.JSONDecodeError):
            jsonreader.from_url(self._url("invalid_claim.json"))

        with self.assertRaises(jsonreader.ContentTypeResponseError):
            jsonreader.from_url(self._url("invalid.txt"))


    @classmethod
    def _url(cls, filename: str) -> str:
        return "http://localhost:%d/Tests/data/%s" % (cls._port, filename)
