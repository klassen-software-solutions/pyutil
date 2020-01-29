"""Tools for downloading JSON from a file or from the web."""

import json
import logging

import requests

import kss.util.contract as contract


class NotOkResponseError(Exception):
    """Exception thrown when a URL requests returns a non-OK response.

    Properties:
        code (int): the HTTP response code
    """
    def __init__(self, response_code: int):
        super().__init__("response_code=%d" % response_code)
        self.response_code = response_code


class ContentTypeResponseError(Exception):
    """Exception thrown when a URL request does return the correct content-type header.

    Properties:
        content_type (str): the returned content-type claim
    """
    def __init__(self, content_type: str):
        super().__init__("content_type=%s" % content_type)
        self.content_type = content_type


def from_file(filename: str):
    """Read a JSON from a file.

    Returns:
        Either returns a List or a Dict depending on the file contents.

    Raises:
        ValueError: if the file name is empty
        FileNotFoundError: if the file cannot be read
        json.decoder.JSONDecodeError: if the file contents cannot be interpreted as JSON
    """
    contract.parameters(lambda: bool(filename))
    logging.debug("Reading '%s' as JSON", filename)
    with open(filename) as infile:
        return json.load(infile)


def from_url(url: str):
    """Read a JSON from a URL.

    Returns:
        Either returns a List or a Dict depending on the returned contents.

    Raises:
        ValueError: if the url is empty
        requests.exceptions.ConnectionError: if the url connection cannot be made
        kss.util.jsonreader.NotOkResponseError: if the url returns a non-OK response
        kss.util.jsonreader.ContentTypeResponseError: if the url does not claim to return
                                                      'application/json'
        json.decoder.JSONDecodeError: if the returned contents cannot be interpreted as JSON
    """
    contract.parameters(lambda: bool(url))
    logging.debug("GET '%s' as JSON", url)
    resp = requests.get(url, headers={'Accept': 'application/json'})
    if not (resp.status_code >= 200 and resp.status_code < 300):
        raise NotOkResponseError(resp.status_code)
    ctype = resp.headers.get('content-type', '')
    if not ctype.startswith('application/json'):
        raise ContentTypeResponseError(ctype)
    return resp.json()
