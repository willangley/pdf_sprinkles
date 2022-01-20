#!/usr/bin/env python
#
# Copyright 2013 Google LLC. All Rights Reserved.
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
"""Converts an PDF to a searchable PDF using Google Cloud Document AI."""

import os
from typing import BinaryIO

from absl import flags
from absl import logging
from google.cloud import documentai_v1 as documentai

FLAGS = flags.FLAGS
flags.DEFINE_string('project_id', None, 'Google Cloud project ID')
flags.DEFINE_enum('location', 'us', ['us', 'eu'],
                  'Location of document processor')
flags.DEFINE_string('processor_id', None, 'ID of document processor')

_documentai_client = None
_max_size = 20 * 1024 * 1024


def get_documentai_client():
  """Lazily constructs and returns a Cloud Document AI client."""
  global _documentai_client
  if not _documentai_client:
    # You must set the api_endpoint if you use a location other than 'us', e.g.:
    opts = {}
    if FLAGS.location == 'eu':
      opts = {'api_endpoint': 'eu-documentai.googleapis.com'}
    _documentai_client = documentai.DocumentProcessorServiceAsyncClient(
        client_options=opts)

  return _documentai_client


async def recognize_content(image_content: bytes):
  """Recognize text in image_content using Document AI."""
  if len(image_content) > _max_size:
    raise ValueError('PDF too large')

  client = get_documentai_client()

  # The full resource name of the processor, e.g.:
  # projects/project-id/locations/location/processor/processor-id
  # You must create new processors in the Cloud Console first
  name = f'projects/{FLAGS.project_id}/locations/{FLAGS.location}/processors/{FLAGS.processor_id}'

  document = {'content': image_content, 'mime_type': 'application/pdf'}

  # Configure the process request
  request = {'name': name, 'raw_document': document}

  logging.info('Recognizing input PDF.')
  result = await client.process_document(request=request)
  return result.document


async def recognize(image: BinaryIO):
  """Recognize text in an image file using Document AI."""
  image.seek(0, os.SEEK_END)
  image_size = image.tell()
  image.seek(0)

  if image_size > _max_size:
    raise ValueError('PDF too large.')

  return await recognize_content(image.read())
