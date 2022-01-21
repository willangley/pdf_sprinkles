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
"""Helpers for Identity-Aware Proxy authorization."""

import json

from google.auth import jwt
from tornado.httpclient import AsyncHTTPClient


async def validate_iap_jwt(iap_jwt, expected_audience):
  """Validate an IAP JWT.

  Args:
    iap_jwt: The contents of the X-Goog-IAP-JWT-Assertion header.
    expected_audience: The Signed Header JWT audience. See
        https://cloud.google.com/iap/docs/signed-headers-howto
        for details on how to get this value.

  Returns:
    (user_id, user_email).
  """

  http_client = AsyncHTTPClient()
  response = await http_client.fetch(
      'https://www.gstatic.com/iap/verify/public_key')
  certs = json.loads(response.body)
  decoded_jwt = jwt.decode(iap_jwt, certs=certs, audience=expected_audience)
  return (decoded_jwt['sub'], decoded_jwt['email'])
