from setuptools import setup, find_packages

VERSION_STRING = '0.0.7'

setup(
    name="kevlar",
    packages=find_packages(),
    version = VERSION_STRING,
    author="Matt Long",
    license="MIT",
    author_email="matt@mattlong.org",
    url="https://github.com/mattlong/kevlar",
    download_url = 'https://github.com/mattlong/kevlar/tarball/' + VERSION_STRING,
    description="Kevlar will be something cool",
    install_requires=['requests>=2.4.1'],
    zip_safe=False,
    include_package_data=True,
    keywords = [],
    classifiers=[],
)
