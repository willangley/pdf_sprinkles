/**
 * @license
 * Copyright 2021 Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @fileoverview JavaScript code for PDF Sprinkles.
 */

function getCookie(key) {
  for (const cookie of document.cookie.split(';')) {
    [ cookieKey, cookieValue ] = cookie.split('=');
    if (key === cookieKey.trim()) {
      return cookieValue.trim();
    }
  }
}

class AlertBox {
  #alertEl;
  #dismissButton;
  static #styleClasses = Object.freeze({
    WORKING: 'alert-working',
    SUCCESS: 'alert-success',
    ERROR: 'alert-error',
  });

  constructor(alertEl) {
    this.#alertEl = alertEl;
    this.#dismissButton = this.#alertEl.querySelector('.dismiss');
    this.#dismissButton.addEventListener('click', () => this.dismissAlert());
  }

  showWorking(message) {
    this.#showAlert(AlertBox.#styleClasses.WORKING, 'Working', message);
  }

  showSuccess(message) {
    this.#showAlert(AlertBox.#styleClasses.SUCCESS, 'Success', message);
  }

  showError(message) {
    this.#showAlert(AlertBox.#styleClasses.ERROR, 'An error occurred', message);
  }

  #showAlert(className, title, message) {
    this.#alertEl.querySelector('.alert-title').innerText = title;
    this.#alertEl.querySelector('.alert-text').innerText = message;

    for (const styleClass in AlertBox.#styleClasses) {
      this.#alertEl.classList.remove(AlertBox.#styleClasses[styleClass]);
    }
    this.#alertEl.classList.add(className);
    this.#alertEl.classList.remove('visually-hidden');
    this.#dismissButton.removeAttribute('hidden');
  }

  dismissAlert() {
    this.#alertEl.querySelector('.alert-title').innerText = '';
    this.#alertEl.querySelector('.alert-text').innerText = '';
    this.#alertEl.classList.add('visually-hidden');
    this.#dismissButton.setAttribute('hidden', '');
  }
}

class PdfSprinkles {
  constructor(formEl, alertBox) {
    this.formEl = formEl;
    this.formEl.addEventListener('submit', (e) => this.submitForm(e));

    this.alertBox = alertBox;
  }

  submitForm(event) {
    event.preventDefault();
    const pdf = document.getElementById('pdf').files[0];
    this.alertBox.showWorking('Uploading file to Document AI');
    fetch(`${this.formEl.action}?filename=${encodeURIComponent(pdf.name)}`, {
      method: 'POST',
      headers: {
        'X-XSRFToken': getCookie('_xsrf'),
      },
      body: pdf,
    }).then(response => {
      if (!response.ok) {
        throw response;
      }
      return response.blob();
    }).then(blob => {
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = pdf.name;
      link.click();
      this.alertBox.showSuccess('Your download will begin shortly');
    }).catch(errorOrResponse => {
      if (errorOrResponse instanceof TypeError) {
        this.alertBox.showError(errorOrResponse.message);
        console.error(errorOrResponse);
      } else {
        return errorOrResponse.text();
      }
    }).then(maybeErrorText => {
      if (!maybeErrorText) {
        return;
      }
      try {
        const structuredError = JSON.parse(maybeErrorText);
        this.alertBox.showError(structuredError.message);
        console.error(structuredError);
      } catch {
        this.alertBox.showError('Backend not reachable.');
        console.error(maybeErrorText);
      }
    });
  }
}

const pdfSprinkles = new PdfSprinkles(
    document.querySelector('.form-container form'),
    new AlertBox(document.querySelector('.alert')));
