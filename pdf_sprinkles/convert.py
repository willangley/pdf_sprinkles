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
from pdf_sprinkles import document_ai_ocr
from pdf_sprinkles import resources
from third_party.hocr_tools import hocr_pdf


FLAGS = flags.FLAGS
flags.DEFINE_string('pdf_info_command', '', 'Command to run pdf_info.')
flags.DEFINE_integer('pdf_info_timeout', 1, 'Timeout in seconds for pdf_info.')


async def convert(input_file: BinaryIO, input_file_name: str,
                  output_file: BinaryIO):
  """Converts an image-only PDF into a PDF with OCR text."""
  document = await document_ai_ocr.recognize(input_file)

  if FLAGS.pdf_info_command:
    pdf_info_command = [resources.GetResourceFilename(FLAGS.pdf_info_command)]
  else:
    pdf_info_command = [sys.executable, '-m', 'pdf_sprinkles.pdf_info']

  # Read mediaboxes from PDFs in a sandbox, limiting how long we'll let it run.
  pdf_info = await asyncio.create_subprocess_exec(
      *pdf_info_command,
      stdin=input_file,
      stdout=asyncio.subprocess.PIPE,
      stderr=subprocess.DEVNULL)
  try:
    pdf_info_result = await asyncio.wait_for(
        pdf_info.communicate(), timeout=FLAGS.pdf_info_timeout)

    # Loading mediaboxes after all coroutines finish ensures we've waited for
    # pdf_info to return. This provides cleaner logs if JSON decode fails.
    mediaboxes = json.loads(pdf_info_result[0])

  # Re-raise exceptions that happen when reading a bad PDF locally with a
  # more user-friendly (and less hacker-friendly) error message.
  except (subprocess.CalledProcessError, asyncio.exceptions.TimeoutError,
          ValueError) as exc:
    raise ValueError("Couldn't read uploaded PDF.") from exc
  # We let gRPC errors reach the user unchanged.

  await hocr_pdf.export_pdf(document, mediaboxes, input_file_name, output_file)
