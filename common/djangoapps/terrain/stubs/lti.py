"""
Stub implementation of LTI Provider.

What is supported:
------------------

1.) This LTI Provider can service only one Tool Consumer at the same time. It is
not possible to have this LTI multiple times on a single page in LMS.

"""

from uuid import uuid4
import textwrap
import urlparse
import urllib
from oauthlib.oauth1.rfc5849 import signature
import oauthlib.oauth1
import hashlib
import base64
import mock
import sys
import requests
import textwrap
from http import StubHttpRequestHandler, StubHttpService

class StubLtiHandler(StubHttpRequestHandler):
    """
    A handler for LTI POST and GET requests.
    """
    DEFAULT_CLIENT_KEY = 'test_client_key'
    DEFAULT_CLIENT_SECRET = 'test_client_secret'
    DEFAULT_LTI_BASE = 'http://127.0.0.1:8034/'
    DEFAULT_LTI_ENDPOINT = 'correct_lti_endpoint'

    def do_GET(self):
        """
        Handle a GET request from the client and sends response back.

        Used for checking LTI Provider started correctly.
        """
        self.send_response(200, 'This is LTI Provider.', {'Content-type': 'text/plain'})

    def do_POST(self):
        """
        Handle a POST request from the client and sends response back.
        """
        headers = {'Content-type': 'text/html'}
        if 'grade' in self.path and self._send_graded_result().status_code == 200:
            status_message = 'LTI consumer (edX) responded with XML content:<br>' + self.server.grade_data['TC answer']
            content = self.create_content(status_message)
            self.send_response(200, content)
        # Respond to request with correct lti endpoint:
        elif self._is_correct_lti_request():
            params = {k: v for k, v in self.post_dict.items() if k != 'oauth_signature'}
            if self.check_oauth_signature(params, self.post_dict.get('oauth_signature', "")):
                status_message = "This is LTI tool. Success."
                # set data for grades what need to be stored as server data
                if 'lis_outcome_service_url' in self.post_dict:
                    referer = urlparse.urlparse(self.headers.getheader('referer'))
                    self.server.referer_host = "{}://{}".format(referer.scheme, referer.netloc)
                    self.server.grade_data = {
                        'callback_url': self.post_dict.get('lis_outcome_service_url'),
                        'sourcedId': self.post_dict.get('lis_result_sourcedid')
                    }
                submit_url = '//%s:%s' % self.server.server_address
                content = self.create_content(status_message, submit_url)
                self.send_response(200, content)
            else:
                content = self.create_content("Wrong LTI signature")
                self.send_response(200, content)
        else:
            content = self.create_content("Invalid request URL")
            self.send_response(500, content)

    def _send_graded_result(self):
        """
        Send grade request.
        """
        values = {
            'textString': 0.5,
            'sourcedId': self.server.grade_data['sourcedId'],
            'imsx_messageIdentifier': uuid4().hex,
        }
        payload = textwrap.dedent("""
            <?xml version = "1.0" encoding = "UTF-8"?>
                <imsx_POXEnvelopeRequest  xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
                  <imsx_POXHeader>
                    <imsx_POXRequestHeaderInfo>
                      <imsx_version>V1.0</imsx_version>
                      <imsx_messageIdentifier>{imsx_messageIdentifier}</imsx_messageIdentifier> /
                    </imsx_POXRequestHeaderInfo>
                  </imsx_POXHeader>
                  <imsx_POXBody>
                    <replaceResultRequest>
                      <resultRecord>
                        <sourcedGUID>
                          <sourcedId>{sourcedId}</sourcedId>
                        </sourcedGUID>
                        <result>
                          <resultScore>
                            <language>en-us</language>
                            <textString>{textString}</textString>
                          </resultScore>
                        </result>
                      </resultRecord>
                    </replaceResultRequest>
                  </imsx_POXBody>
                </imsx_POXEnvelopeRequest>
        """)
        data = payload.format(**values)

        if getattr(self.server, 'use_real_callback_url', None):
            # Use exact URL that was sent from TC when using this Stub LTI server
            # as TP in real standalone environment.
            url = self.server.grade_data['callback_url']
        else:
            # Use relative URL when using TP locally for manual testing or jenkins.
            relative_url = urlparse.urlparse(self.server.grade_data['callback_url']).path
            url = self.server.referer_host + relative_url

        headers = {'Content-Type': 'application/xml', 'X-Requested-With': 'XMLHttpRequest'}
        headers['Authorization'] = self.oauth_sign(url, data)

        # We can't mock requests in unit tests, because we use them, but we need
        # them to be mocked only for this one case.
        if self.server.config.get('run_inside_unittest_flag', None):
            response = mock.Mock(status_code=200, url=url, data=data, headers=headers)
            return response
        # Send request ignoring verification of SSL certificate
        response = requests.post(
            url,
            data=data,
            headers=headers,
            verify=False
        )
        self.server.grade_data['TC answer'] = response.content
        return response

    def create_content(self, response_text, submit_url=None):
        """
        Return content (str) either for launch, send grade or get result from TC.
        """
        submit_form = ''
        if submit_url:
            submit_form = textwrap.dedent("""
                <form action="{}/grade" method="post">
                    <input type="submit" name="submit-button" value="Submit">
                </form>
            """).format(submit_url)

        response_str = textwrap.dedent("""
                <html>
                    <head>
                        <title>TEST TITLE</title>
                    </head>
                    <body>
                        <div>
                            <h2>IFrame loaded</h2>
                            <h3>Server response is:</h3>
                            <h3 class="result">{}</h3>

                        </div>
                        {}
                    </body>
                </html>
            """).format(response_text, submit_form)

        return urllib.unquote(response_str)

    def _is_correct_lti_request(self):
        '''
        If url to LTI Provider is correct.
        '''
        lti_endpoint = self.server.config.get('lti_endpoint', self.DEFAULT_LTI_ENDPOINT)
        return lti_endpoint in self.path

    def oauth_sign(self, url, body):
        """
        Signs request and returns signed body and headers.
        """
        client_key = self.server.config.get('client_key', self.DEFAULT_CLIENT_KEY)
        client_secret = self.server.config.get('client_secret', self.DEFAULT_CLIENT_SECRET)
        client = oauthlib.oauth1.Client(
            client_key=unicode(client_key),
            client_secret=unicode(client_secret)
        )
        headers = {
            # This is needed for body encoding:
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        #Calculate and encode body hash. See http://oauth.googlecode.com/svn/spec/ext/body_hash/1.0/oauth-bodyhash.html
        sha1 = hashlib.sha1()
        sha1.update(body)
        oauth_body_hash = base64.b64encode(sha1.digest())
        __, headers, __ = client.sign(
            unicode(url.strip()),
            http_method=u'POST',
            body={u'oauth_body_hash': oauth_body_hash},
            headers=headers
        )
        headers = headers['Authorization'] + ', oauth_body_hash="{}"'.format(oauth_body_hash)
        return headers

    def check_oauth_signature(self, params, client_signature):
        """
        Checks oauth signature from client.

        `params` are params from post request except signature,
        `client_signature` is signature from request.

        Builds mocked request and verifies hmac-sha1 signing::
            1. builds string to sign from `params`, `url` and `http_method`.
            2. signs it with `client_secret` which comes from server settings.
            3. obtains signature after sign and then compares it with request.signature
            (request signature comes form client in request)

        Returns `True` if signatures are correct, otherwise `False`.

        """
        client_secret = unicode(self.server.config.get('client_secret', self.DEFAULT_CLIENT_SECRET))
        lti_base = self.server.config.get('lti_base', self.DEFAULT_LTI_BASE)
        lti_endpoint = self.server.config.get('lti_endpoint', self.DEFAULT_LTI_ENDPOINT)
        url = lti_base + lti_endpoint

        request = mock.Mock()
        request.params = [(unicode(k), unicode(v)) for k, v in params.items()]
        request.uri = unicode(url)
        request.http_method = u'POST'
        request.signature = unicode(client_signature)

        return signature.verify_hmac_sha1(request, client_secret)


class StubLtiService(StubHttpService):
    """
    A stub LTI provider server that responds
    to POST and GET requests to localhost.
    """

    HANDLER_CLASS = StubLtiHandler

if __name__ == "__main__":
    service = StubLtiService(8034)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        service.shutdown()
        exit(0)
