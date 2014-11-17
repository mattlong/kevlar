from setuptools import setup, find_packages

setup(
    name="kevlar",
    packages=find_packages(),
    version='0.0.1',
    author="Matt Long",
    license="ISC",
    author_email="matt@mattlong.org",
    url="https://github.com/mattlong/kevlar",
    description="Kevlar will be something cool",
    #long_description="",
    install_requires=[],
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: ISC License (ISCL)',
    ],
)
