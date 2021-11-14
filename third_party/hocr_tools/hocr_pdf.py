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

"""Creates a searchable PDF from a Document AI API response.

Originally created a searchable PDF from a pile of HOCR + JPEG, as output by
Tesseract. The two are very similar problems :).
"""

import asyncio
import io

from absl import flags
from absl import logging
from bidi.algorithm import get_display
from google.cloud import documentai_v1 as documentai
import img2pdf
from pikepdf import Pdf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


FLAGS = flags.FLAGS
flags.DEFINE_float('min_confidence', 0.9, 'Minimum confidence of lines to '
                   'include in output.')


async def export_pdf(document, mediaboxes, title, output_file):
  """Create a searchable PDF from an input file and a Document."""
  logging.info('Exporting recognized PDF with %d pages.', len(mediaboxes))

  load_noto_sans()
  text_buf = io.BytesIO()

  pdf = Canvas(text_buf, pageCompression=1)
  pdf.setTitle(title)

  for mediabox, page in zip(mediaboxes, document.pages):
    await asyncio.sleep(0)
    pdf.setPageSize(mediabox)
    add_text_layer(pdf, document, page, *mediabox)
    pdf.showPage()

  pdf.save()

  with Pdf.open(text_buf) as text_pdf:
    for text_page, page in zip(text_pdf.pages, document.pages):
      await asyncio.sleep(0)
      _, _, width, height = text_page.trimbox
      width = float(width)
      height = float(height)

      layout_fun = img2pdf.get_layout_fun((width, height))
      bg_buf = io.BytesIO()
      img2pdf.convert(page.image.content, layout_fun=layout_fun,
                      outputstream=bg_buf)
      with Pdf.open(bg_buf) as bg_pdf:
        text_page.add_underlay(bg_pdf.pages[0])

    text_pdf.save(output_file)


def add_text_layer(pdf, document, page, width, height):
  """Draws an invisible text layer for OCR data."""
  for line in page.lines:
    if line.layout.confidence < FLAGS.min_confidence:
      continue

    left, top, _, bottom = bbox(line.layout)
    left *= width
    top *= height
    bottom *= height

    # Heuristic from old hocr-pdf: assume 30% of line is descenders
    base = bottom - 0.7 * (bottom - top)

    tokens = [token for token in page.tokens
              if (start_index(token.layout) >= start_index(line.layout) and
                  end_index(token.layout) <= end_index(line.layout))]

    text = pdf.beginText()
    text.setTextRenderMode(3)  # invisible
    text.setFont('Noto Sans', 8)
    text.setTextOrigin(left, height - base)

    for token in tokens:
      rawtext = get_text(token.layout, document)
      if not rawtext:
        continue
      font_width = pdf.stringWidth(rawtext, 'Noto Sans', 8)
      if font_width <= 0:
        continue

      token_left, _, token_right, _ = bbox(token.layout)
      token_left *= width
      token_right *= width

      box_width = token_right - token_left
      cursor = text.getStartOfLine()
      dx = token_left - cursor[0]
      text.moveCursor(dx, 0)
      text.setHorizScale(100.0 * box_width / font_width)
      rawtext = get_display(rawtext)
      text.textOut(rawtext)

    pdf.drawText(text)


def bbox(layout):
  left = min(v.x for v in layout.bounding_poly.normalized_vertices)
  top = max(v.y for v in layout.bounding_poly.normalized_vertices)
  right = max(v.x for v in layout.bounding_poly.normalized_vertices)
  bottom = min(v.y for v in layout.bounding_poly.normalized_vertices)
  return [left, top, right, bottom]


def start_index(layout):
  return layout.text_anchor.text_segments[0].start_index


def end_index(layout):
  return layout.text_anchor.text_segments[-1].end_index


def get_text(doc_element: documentai.types.Document.Page.Layout,
             document: documentai.types.Document):
  """Converts Document AI offsets to text snippets."""
  response = ''
  # If a text segment spans several lines, it will
  # be stored in different text segments.
  for segment in doc_element.text_anchor.text_segments:
    text_start_index = (
        int(segment.start_index)
        if segment in doc_element.text_anchor.text_segments
        else 0
    )
    text_end_index = int(segment.end_index)
    response += document.text[text_start_index:text_end_index]
  return response


_fonts_loaded = False


def load_noto_sans():
  global _fonts_loaded
  if not _fonts_loaded:
    _fonts_loaded = True
    pdfmetrics.registerFont(TTFont(
        'Noto Sans', 'third_party/noto-fonts/NotoSans-Regular.ttf'))
