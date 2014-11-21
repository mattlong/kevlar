from setuptools import setup, find_packages

from kevlar import __version__

setup(
    name="kevlar",
    packages=find_packages(),
    version = __version__,
    author="Matt Long",
    license="MIT",
    author_email="matt@mattlong.org",
    url="https://github.com/mattlong/kevlar",
    download_url = 'https://github.com/mattlong/kevlar/tarball/' + __version__,
    description="Kevlar will be something cool",
    install_requires=['requests>=2.4.1'],
    zip_safe=False,
    include_package_data=True,
    keywords = [],
    classifiers=[],
)
