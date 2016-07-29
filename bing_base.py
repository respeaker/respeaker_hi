
import json
import uuid
import io
from monotonic import monotonic
from urllib import urlencode
from urllib2 import Request, urlopen, URLError, HTTPError


class RequestError(Exception):
    pass

class UnknownValueError(Exception):
    pass

class LocaleError(Exception):
    pass

class BingBase():
    def __init__(self, key):
        self.key = key

    def token(self):
        access_token, expire_time = getattr(self, "bing_cached_access_token", None), \
                                    getattr(self, "bing_cached_access_token_expiry", None)

        if expire_time is None or monotonic() > expire_time:  # first credential request, or the access token from the previous one expired
            # get an access token using OAuth
            credential_url = "https://oxford-speech.cloudapp.net/token/issueToken"
            credential_request = Request(credential_url, data=urlencode({
                "grant_type": "client_credentials",
                "client_id": "python",
                "client_secret": self.key,
                "scope": "https://speech.platform.bing.com"
            }).encode("utf-8"))
            start_time = monotonic()
            try:
                credential_response = urlopen(credential_request)
            except HTTPError as e:
                raise RequestError("recognition request failed: {0}".format(
                    getattr(e, "reason", "status {0}".format(e.code))))  # use getattr to be compatible with Python 2.6
            except URLError as e:
                raise RequestError("recognition connection failed: {0}".format(e.reason))
            credential_text = credential_response.read().decode("utf-8")
            credentials = json.loads(credential_text)
            access_token, expiry_seconds = credentials["access_token"], float(credentials["expires_in"])

            # save the token for the duration it is valid for
            self.bing_cached_access_token = access_token
            self.bing_cached_access_token_expiry = start_time + expiry_seconds

        return access_token
