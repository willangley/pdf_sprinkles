from setuptools import setup

setup(
    name='pdf_sprinkles',
    version='0.1.0',
    author='Will Angley',
    author_email='willangley@google.com',
    packages=[
        'pdf_sprinkles',
        'third_party.hocr_tools'
    ],
    scripts=[
        'pdf_sprinkles_cli.py',
        'pdf_sprinkles_web.py'
    ],
    include_package_data=True,
)
