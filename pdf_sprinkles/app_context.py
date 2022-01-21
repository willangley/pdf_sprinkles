# Copyright 2021 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""app_context: cooperating request handler and logging for PDF Sprinkles.

* Sends logs to the Cloud Logging API with the appropriate resource
  and labels for App Engine logs.
* Optionally, when `--expected_audience` is set, enforces Cloud IAP protection
  for requests to this handler.
"""

import contextvars
import re

from absl import flags
from google.cloud.logging import handlers
from pdf_sprinkles import iap_auth
import tornado.web

FLAGS = flags.FLAGS
flags.DEFINE_string('expected_audience', None, 'Expected audience for IAP.')

_TRACE_ID_LABEL = 'appengine.googleapis.com/trace_id'

http_request = contextvars.ContextVar('http_request', default={})
trace_id = contextvars.ContextVar('trace_id', default=None)
span_id = contextvars.ContextVar('span_id', default=None)


def get_request_data():
  return http_request.get(), trace_id.get(), span_id.get()


def parse_trace_span(header: str):
  """Parses a Cloud Tracing span from its header."""
  spans = re.match(r'^(?P<trace_id>\w+)(?:/(?P<span_id>\w+))?', header)
  if not spans:
    return None, None
  else:
    return (spans.groupdict().get('trace_id'),
            spans.groupdict().get('span_id'))


def set_request_data(request: tornado.httputil.HTTPServerRequest):
  """Records request data in context vars for async logging."""
  http_request.set({
      'requestMethod': request.method,
      'requestUrl': request.uri,
      'requestSize': len(request.body) if isinstance(request.body, str) else 0,
      'userAgent': request.headers.get('User-Agent', ''),
      'remoteIp': request.remote_ip,
      'referer': request.headers.get('Referer', ''),
      'protocol': request.protocol,
  })

  extracted = parse_trace_span(request.headers.get('X-Cloud-Trace-Context', ''))
  trace_id.set(extracted[0])
  span_id.set(extracted[1])


class RequestHandler(tornado.web.RequestHandler):
  """Request handler that records trace context."""

  async def prepare(self):
    set_request_data(self.request)

    if FLAGS.expected_audience and self.request.path != '/_ah/warmup':
      iap_jwt = self.request.headers['X-Goog-IAP-JWT-Assertion']
      _, user_email = await iap_auth.validate_iap_jwt(iap_jwt,
                                                      FLAGS.expected_audience)
      self.current_user = user_email

    return super().prepare()


class LoggingHandler(handlers.AppEngineHandler):
  """Sets user overrides for App Engine request logging."""

  def emit(self, record):
    inferred_http, inferred_trace, _ = get_request_data()
    if inferred_http:
      setattr(record, 'http_request', inferred_http)
    if inferred_trace:
      setattr(record, 'trace',
              f'projects/{self.project_id}/traces/{inferred_trace}')
      setattr(record, 'labels', {_TRACE_ID_LABEL: inferred_trace})
    super().emit(record)
