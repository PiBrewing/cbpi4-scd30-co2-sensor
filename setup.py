from setuptools import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-scd30_CO2_Sensor',
      version='0.0.1',
      description='CraftBeerPi4 Plugin for SCD30 based CO2 Sensor',
      author='Alexander Vollkopf',
      author_email='avollkopf@web.de',
      url='https://github.com/avollkopf/cbpi4-scd30-co2-sensor',
      license='GPLv3',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-scd30_CO2_Sensor': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-scd30_CO2_Sensor'],
        install_requires=[
        'cbpi>=4.0.0.33',
        'smbus2',
        'scd30_i2c',
  ],
  long_description=long_description,
  long_description_content_type='text/markdown'

     )
