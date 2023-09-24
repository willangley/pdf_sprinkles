# hocr-tools

https://github.com/ocropus/hocr-tools

This directory contains a forked and heavily modified copy of `hocr-pdf` from
`hocr-tools`.  It no longer consumes the hOCR format and instead directly uses
output from Google's Document AI API.

It also no longer uses its bundled glyphless font; text in this glyphless font
was difficult to select using Chrome. It embeds Noto Sans as a workaround until
this can be investigated.

## License

`hocr-tools` is licensed under the Apache License, v2.0. A copy of the original
license is included in this directory as LICENSE.
