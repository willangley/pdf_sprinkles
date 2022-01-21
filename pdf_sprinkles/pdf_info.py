#!/usr/bin/env python
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
"""pdf_info.py: gets information from a PDF."""

import enum
import json
import mmap
import sys
from typing import Sequence

from absl import app
from absl import flags
from pikepdf import Pdf
import seccomp

FLAGS = flags.FLAGS
flags.DEFINE_bool('sandbox', True, 'Runs PDF parsing inside a seccomp sandbox.')


class Futex(enum.IntFlag):
  """Futex operations from <linux/futex.h>."""
  FUTEX_WAKE = 1
  FUTEX_WAIT_BITSET = 9
  FUTEX_PRIVATE_FLAG = 128
  FUTEX_CLOCK_REALTIME = 256


def get_mediaboxes(pdf: Pdf):
  """Gets effective media boxes (page boundaries) from a PDF.

  This applies rotations, since Document AI transparently applies rotations too.

  Args:
      pdf: an open pikepdf.Pdf instance

  Returns:
      An array of (width, height) media boxes, with one element per page of pdf.
  """

  mediaboxes = []
  for page in pdf.pages:
    ll_x, ll_y, ur_x, ur_y = page.mediabox
    width = ur_x - ll_x
    height = ur_y - ll_y

    rotate = page.obj.get('/Rotate', 0)
    if rotate == 90 or rotate == 270:
      width, height = height, width

    mediaboxes.append((float(width), float(height)))
  return mediaboxes


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  if FLAGS.sandbox:
    f = seccomp.SyscallFilter(defaction=seccomp.KILL)
    f.add_rule(seccomp.ALLOW, 'brk')
    f.add_rule(seccomp.ALLOW, 'futex',
               seccomp.Arg(1, seccomp.EQ, Futex.FUTEX_WAKE))
    f.add_rule(seccomp.ALLOW, 'futex',
               seccomp.Arg(1, seccomp.EQ, Futex.FUTEX_WAKE
                           | Futex.FUTEX_PRIVATE_FLAG))  # FUTEX_WAKE_PRIVATE

    f.add_rule(seccomp.ALLOW, 'read',
               seccomp.Arg(0, seccomp.EQ, sys.stdin.fileno()))
    f.add_rule(seccomp.ALLOW, 'lseek',
               seccomp.Arg(0, seccomp.EQ, sys.stdin.fileno()))
    f.add_rule(seccomp.ALLOW, 'write',
               seccomp.Arg(0, seccomp.EQ, sys.stdout.fileno()))
    f.add_rule(seccomp.ALLOW, 'write',
               seccomp.Arg(0, seccomp.EQ, sys.stderr.fileno()))

    f.add_rule(seccomp.ALLOW, 'rt_sigaction')
    f.add_rule(seccomp.ALLOW, 'rt_sigreturn')
    f.add_rule(seccomp.ALLOW, 'sigaltstack')
    f.add_rule(seccomp.ALLOW, 'fstat',
               seccomp.Arg(0, seccomp.EQ, sys.stdin.fileno()))  # App Engine
    f.add_rule(seccomp.ALLOW, 'exit_group')

    # Allow Python to allocate and unallocate memory.
    # https://github.com/seccomp/libseccomp/commit/4f34c6eb17c2ffcb0fce5911ddbc161d97517476
    f.add_rule(
        seccomp.ALLOW, 'mmap', seccomp.Arg(0, seccomp.EQ, 0),
        seccomp.Arg(3, seccomp.EQ, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS))
    f.add_rule(seccomp.ALLOW, 'munmap')

    # Allow background threads to be background threads
    f.add_rule(seccomp.ALLOW, 'tgkill')
    f.add_rule(seccomp.ALLOW, 'gettid')
    f.add_rule(seccomp.ALLOW, 'getpid')
    f.add_rule(
        seccomp.ALLOW, 'futex',
        seccomp.Arg(
            1, seccomp.EQ, Futex.FUTEX_WAIT_BITSET | Futex.FUTEX_PRIVATE_FLAG
            | Futex.FUTEX_CLOCK_REALTIME))

    f.load()

  with Pdf.open(sys.stdin.buffer) as pdf:
    print(json.dumps(get_mediaboxes(pdf)))


if __name__ == '__main__':
  app.run(main)
