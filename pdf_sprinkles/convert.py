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
"""pdf_sprinkles: sprinkles text in your PDFs.

More seriously, it converts an PDF to a searchable PDF using Google Cloud
Document AI.
"""

import asyncio
import json
import subprocess
import sys
from typing import BinaryIO

from absl import flags
from absl import logging
from google.cloud import documentai_v1 as documentai
from pdf_sprinkles import document_ai_ocr
from third_party.hocr_tools import hocr_pdf
import tornado.process

FLAGS = flags.FLAGS
flags.DEFINE_integer('pdf_info_timeout', 1, 'Timeout in seconds for pdf_info.')


async def convert(input_file: BinaryIO, input_file_name: str,
                  output_file: BinaryIO):
  """Converts an image-only PDF into a PDF with OCR text."""
  recognizer = document_ai_ocr.recognize(input_file)

  # Read mediaboxes from PDFs in a sandbox. Limit how much we'll read from the
  # sandbox, and how long we'll let it run.
  #
  # Normally you'd use `head` in a pipeline to limit reads, but it's not
  # available in the App Engine runtime. So we limit reads with asyncio instead.
  pdf_info = tornado.process.Subprocess(
      [sys.executable, '-m', 'pdf_sprinkles.pdf_info'],
      stdin=input_file,
      stdout=tornado.process.Subprocess.STREAM,
      stderr=subprocess.DEVNULL)
  pdf_info_reader = pdf_info.stdout.read_bytes(4 * 1024, partial=True)
  pdf_info_waiter = asyncio.wait_for(
      pdf_info.wait_for_exit(), timeout=FLAGS.pdf_info_timeout)

  try:
    for coro in asyncio.as_completed(
        [recognizer, pdf_info_reader, pdf_info_waiter]):
      result = await coro

      # coro might not equal a coroutine passed to asyncio.as_completed,
      # so dispatch on result types instead
      if isinstance(result, int):  # pdf_info return code
        logging.debug('convert.pdf_info_waiter: %d', result)
      elif isinstance(result, bytes):  # pdf_info stdout
        logging.debug('convert.pdf_info_reader: %d bytes', len(result))
        mediaboxes_buf = result
        pdf_info.stdout.close()  # close the pipe like `head` does.
      elif isinstance(result, documentai.Document):  # Document AI result
        logging.debug('convert.recognizer')
        document = result

    # Loading mediaboxes after all coroutines finish ensures we've waited for
    # pdf_info to return. This provides cleaner logs if JSON decode fails.
    mediaboxes = json.loads(mediaboxes_buf)

  # Re-raise exceptions that happen when reading a bad PDF locally with a
  # more user-friendly (and less hacker-friendly) error message.
  except (subprocess.CalledProcessError, asyncio.exceptions.TimeoutError,
          ValueError) as exc:
    raise ValueError("Couldn't read uploaded PDF.") from exc
  # We let gRPC errors reach the user unchanged.
  finally:
    # in case of exception:
    # - the pipe from pdf_info may still be open, and
    # - the pdf_info process may still be running.
    #
    # close the pipe and kill the process to prevent leaks.
    if not pdf_info.stdout.closed():
      pdf_info.stdout.close()
    if pdf_info.proc.poll() is None:
      pdf_info.proc.kill()

  await hocr_pdf.export_pdf(document, mediaboxes, input_file_name, output_file)
