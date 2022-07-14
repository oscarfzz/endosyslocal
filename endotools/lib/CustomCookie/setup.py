from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='CustomCookie',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          "AuthKit>=0.4,<=0.5",
      ],
      entry_points="""
      # -*- Entry points: -*-
      [authkit.method]
      customcookie=customcookie:make_handler
      """,
      )
