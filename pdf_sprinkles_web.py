#!/usr/bin/env python3
#
# Copyright 2021 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Web app that serves pdf_sprinkles."""

import base64
import logging as py_logging
import os.path
import tempfile
import traceback
from typing import Sequence

from absl import app
from absl import flags
from absl import logging
import document_ai_ocr
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import secretmanager
import google.cloud.logging
from google.cloud.logging.handlers import AppEngineHandler
from google.cloud.logging.handlers import setup_logging
import pdf_sprinkles
from third_party.hocr_tools import hocr_pdf
import tornado.httpserver
import tornado.ioloop
import tornado.web
import trace_context
import uimodules


FLAGS = flags.FLAGS
flags.DEFINE_integer('port', 8888, 'port to listen to.')
flags.DEFINE_string('address', '127.0.0.1', 'address to bind to.')
flags.DEFINE_boolean('debug', False, 'Starts Tornado in debugging mode.')
flags.DEFINE_string('cookie_secret_id', None,
                    'ID of a cookie secret in Secrets Manager')
flags.DEFINE_string(
    'self_link', None, 'If set, displays a self link in the header.')
flags.DEFINE_boolean('cloud_logging', False, 'Use cloud logging.')


class MainHandler(trace_context.RequestHandler):
  """Display's the application's UI."""

  def get(self):
    self.render('index.html', self_link=FLAGS.self_link)


class WarmupHandler(trace_context.RequestHandler):
  """Warms up the application for better performance on App Engine."""

  def get(self):
    document_ai_ocr.get_documentai_client()
    hocr_pdf.load_noto_sans()


@tornado.web.stream_request_body
class RecognizeHandler(trace_context.RequestHandler):
  """Recognize text in a PDF."""

  def initialize(self):
    self.input_file = tempfile.TemporaryFile()
    self.output_file = tempfile.TemporaryFile()

  def data_received(self, chunk):
    self.input_file.write(chunk)

  async def post(self):
    filename = self.get_argument('filename')
    await pdf_sprinkles.convert(self.input_file, filename, self.output_file)

    self.output_file.seek(0, os.SEEK_END)
    output_size = self.output_file.tell()
    self.output_file.seek(0)

    if output_size > 32 * 1024 * 1024:
      raise ValueError('Output PDF too large.')

    logging.info('Serving exported PDF')
    encoded_filename = tornado.escape.url_escape(filename, plus=False)
    self.set_header(
        'Content-Disposition',
        f"attachment; filename*=utf-8''{encoded_filename}")
    self.set_header('Content-Type', 'application/pdf')
    self.set_header('Cache-Control', 'private')

    while True:
      data = self.output_file.read(65536)
      if not data: break
      self.write(data)
      await self.flush()

    self.finish()

  def write_error(self, status_code: int, **kwargs):
    response = {}
    if 'exc_info' in kwargs:
      _, exc_value, _ = kwargs['exc_info']
      response['message'] = (
          exc_value.message if isinstance(exc_value, GoogleAPICallError)
          else str(exc_value))
      if self.settings.get('serve_traceback'):
        response['traceback'] = traceback.format_exception(*kwargs['exc_info'])
    else:
      response['message'] = f'{status_code}: {self._reason}'

    self.finish(response)


class StaticFileHandler(tornado.web.StaticFileHandler,
                        trace_context.RequestHandler):
  """Adds App Engine tracing info to static file requests."""
  pass


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  if FLAGS.cloud_logging:
    cloud_logging_client = google.cloud.logging.Client()
    handler = cloud_logging_client.get_default_handler()
    if isinstance(handler, AppEngineHandler):
      handler = trace_context.AppEngineHandler(cloud_logging_client)
    setup_logging(handler)
    py_logging.root.removeHandler(logging.get_absl_handler())

  settings = {
      'ui_modules': uimodules,
  }

  if FLAGS.cookie_secret_id:
    secret_manager_client = secretmanager.SecretManagerServiceClient()
    secret_path = secret_manager_client.secret_path(
        FLAGS.project_id, FLAGS.cookie_secret_id)
    versions = secret_manager_client.list_secret_versions(request={
        'parent': secret_path,
        'filter': 'state:ENABLED',
    })

    cookie_secrets = {}
    for version in versions:
      parsed_version = secret_manager_client.parse_secret_version_path(
          version.name)
      response = secret_manager_client.access_secret_version(
          request={'name': version.name})
      cookie_secrets[int(parsed_version['secret_version'])] = (
          base64.b64decode(response.payload.data))

    if not cookie_secrets:
      logging.fatal('No enabled versions found for secret %s', secret_path)

    settings.update({
        'cookie_secret': cookie_secrets,
        'key_version': max(cookie_secrets.keys()),
        'xsrf_cookies': True,
    })

  application = tornado.web.Application(
      [
          (r'/', MainHandler, None, 'main'),
          (r'/_ah/warmup', WarmupHandler),
          (r'/recognize', RecognizeHandler, None, 'recognize'),
      ],
      static_handler_class=StaticFileHandler,
      static_path=os.path.join(os.path.dirname(__file__), 'static'),
      template_path=os.path.join(os.path.dirname(__file__), 'templates'),
      debug=FLAGS.debug,
      **settings,
  )

  server_settings = {}
  if os.environ.get('GAE_VERSION', ''):
    server_settings.update({
        'trusted_downstream': ['169.254.1.1'],
        'xheaders': True,
    })

  server = tornado.httpserver.HTTPServer(application, **server_settings)
  server.bind(FLAGS.port, FLAGS.address, reuse_port=True)
  server.start()

  logging.info('Started server on %s:%d', FLAGS.address, FLAGS.port)
  tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
  app.run(main)

