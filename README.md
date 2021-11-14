# `pdf_sprinkles`: sprinkles text in your PDFs

`pdf_sprinkles` remotely OCRs a PDF with Google Cloud Document AI, and returns
the result as a PDF with searchable text.

It runs on the command-line or as a web server. The server version can be
deployed to App Engine easily.

`pdf_sprinkles` has only been tested with English-language text, but it should
work for most European languages supported by the Document AI API today. It is
known **not** to work with RTL languages and with CJK scripts currently.

## Installation

`pdf_sprinkles` is experimental, so it's not packaged yet. To install:

* Set up Google Cloud Document AI, following the [quickstart].
* Clone this repository and `cd` to it.
* Create a virtualenv, `pdf_sprinkles$ virtualenv env`.
* Install requirements, `pdf_sprinkles$ pip install -r requirements.txt`.
* Save your `location`, `processor_id` and `project_id` in a flagfile:

    ```
    pdf_sprinkles$ cat >flagfile
    --location='your-location' # 'us' or 'eu'
    --processor_id='your-processor-id'
    --project_id='your-project-id'
    pdf_sprinkles$
    ```
## Quickstart

Activate the virtualenv:

* `pdf_sprinkles$ . env/bin/activate`

and invoke `pdf_sprinkles_cli.py` with your input and output:

* `(env) pdf_sprinkles$ ./pdf_sprinkles_cli.py --flagfile=flagfile --input=scan.pdf --output=scan-ocr.pdf`

or invoke `pdf_sprinkles_web.py` and visit it at http://localhost:8888/ :

* `(env) pdf_sprinkles$ ./pdf_sprinkles_web.py --flagfile=flagfile`

## Usage

### pdf\_sprinkles\_web.py

```
USAGE: ./pdf_sprinkles_web.py [flags]
```

`./pdf_sprinkles_web.py`:

* `--address`: Address to bind to.
    (default: '127.0.0.1')
* `--[no]cloud_logging`: Use cloud logging.
    (default: 'false')
* `--cookie_secret_id`: ID of a cookie secret in Secrets Manager
* `--[no]debug`: Starts Tornado in debugging mode.
    (default: 'false')
* `--port`: Port to bind to
    (default: '8888')
    (an integer)
* `--self_link`: If set, displays a self link in the header.

`app_context`:

* `--expected_audience`: Expected audience for IAP.

`uimodules`:

* `--faq_link`: If set, displays an FAQ link in the footer.
* `--mailing_list_link`: If set, displays a mailing list link in the footer.

### pdf\_sprinkles\_cli.py

```
USAGE: ./pdf_sprinkles_cli.py [flags]
```

`./pdf_sprinkles_cli.py`:

* `--input`: Path to input file
* `--output`: Path to output file

### Shared Flags

These flags can be set for both the CLI and Web frontends.

`document_ai_ocr`:

*  `--location`: `<us|eu>`: Location of document processor
    (default: 'us')
* `--processor_id`: ID of document processor
* `--project_id`: Google Cloud project ID

`third_party.hocr_tools.hocr_pdf`:

* `--min_confidence`: Minimum confidence of lines to include in output.
    (default: '0.9') (a number)

`pdf_sprinkles` uses [Abseil Flags], so you can define rarely changing flags in
a file and import it with `--flagfile=FILENAME`.

## Running on App Engine

> :warning: processing a document with Document AI OCR costs ≈ 10× – 100× as 
> much as serving a copy of it from Cloud Storage.
> 
> * ⛔ Don't leave this app running on the public Internet. It can rapidly turn
>   into a denial-of-wallet attack.
> * ✅ Do set up [Identity-Aware Proxy](#identity-aware-proxy) and restrict 
>   access to family/friends/organizations you want to buy scans for.

`pdf_sprinkles` ships with configs to run on a Python 3 Standard Environment
runtime. It uses `supervisord`, with listening port and number of workers
controlled by environment variables.

### Set up config files

1. copy `app.yaml.example` to `app.yaml`.
1. Adjust instance size / workers / scaling to taste. For instance, if you
   have a busy environment and don't mind a few hundred dollars a month in
   costs, set:

   ```yaml
    env_variables:
        WORKERS: 4
    instance_class: F4_1G

    automatic_scaling:
      min_idle_instances: 1
   ```

1. copy `supervisord.conf.example` to `supervisord.conf`.
1. update flags in `supervisord.conf` to match the flagfile.

### Cookie Secret

The app can uses a cookie secret for XSRF protection. Since checking secrets in
to Git is a bad idea, we use [Secret Manager] instead.

You'll need to set this up on first use.

1. Generate a 32-byte symmetric key:

    ```
    $ head -c 32 /dev/urandom | base64
    BNUV6qSX0YOjatf4kfYBHUKVlD3kw+89hLia5M1Pduw=
    $
    ```

    and store it in Secret Manager.

1. Grant the app service account access to the secret and its versions (see IAM
   Roles, below.)
1. Set `--cookie_secret_id` in `supervisord.conf` to match.

### IAM Roles

The service account for the app needs project-level IAM roles:

* `roles/documentai.apiUser`, Document AI > Cloud DocumentAI API User
* `roles/logging.logWriter`, Logging > Logs Writer

and needs access to its cookie secret, granted with:

* `roles/secretmanager.secretAccessor`, Secret Manager Secret Accessor
* `roles/secretmanager.viewer`, Secret Manager Viewer

### Deploy

Run `pdf_sprinkles$ gcloud app deploy`.

### Identity-Aware Proxy

PDF Sprinkles supports running behind Identity-Aware Proxy. To use this:

1. Follow the [IAP Quickstart][iap-quickstart] documentation, starting at
    **Enabling IAP**.
1. Set `--expected_audience` in `supervisord.conf` to match the IAP Audience.
1. Deploy the app again with `pdf_sprinkles$ gcloud app deploy`.
1. Send [test requests][iap-test-requests] to verify everything works properly.

## License

`pdf_sprinkles` is licensed under the Apache License, Version 2.0.

[Abseil Flags]: https://abseil.io/docs/python/guides/flags
[iap-quickstart]: https://cloud.google.com/iap/docs/app-engine-quickstart#enabling_iap
[iap-test-requests]: https://cloud.google.com/iap/docs/query-parameters-and-headers-howto#testing_jwt_verification
[quickstart]: https://cloud.google.com/document-ai/docs/quickstart-client-libraries?hl=en_US
[Secret Manager]: https://cloud.google.com/secret-manager
