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

"""Converts an PDF to a searchable PDF using Google Cloud Document AI."""

import asyncio
import os.path
import sys
from typing import Sequence

from absl import app
from absl import flags
from pdf_sprinkles.convert import convert


FLAGS = flags.FLAGS
flags.DEFINE_string('input', None, 'Path to input file')
flags.DEFINE_string('output', None, 'Path to output file')


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  with open(FLAGS.input, 'rb') as input_file, open(
      FLAGS.output, 'wb') if FLAGS.output else open(
          sys.stdout.fileno(), 'wb', closefd=False) as output_file:
    asyncio.run(
        convert(input_file, os.path.basename(FLAGS.input), output_file))


if __name__ == '__main__':
  app.run(main)
