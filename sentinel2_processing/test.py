import requests
from requests.adapters import HTTPAdapter
import requests.exceptions as e
from urllib3 import Retry
import http

http.client.HTTPConnection.debuglevel = 1

retry_strategy = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)


DEFAULT_TIMEOUT = 10 # seconds
assert_status_hook = lambda response, *args, **kwargs: response.raise_for_status()
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

http = requests.Session()
http.hooks["response"] = [assert_status_hook]
http.mount("https://", TimeoutHTTPAdapter(max_retries=retry_strategy))
http.mount("http://", TimeoutHTTPAdapter(max_retries=retry_strategy))

# 通常为特定的请求重写超时时间
try:
    response = http.get("https://httpbin.org/status/503")
except e.RequestException as ee:
    http.close()
    print(ee)
else:
    print(response.status_code)
finally:
    http.close()

