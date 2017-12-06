from setuptools import setup

setup(name='orbbit',
      version='0.1',
      description='A language-independent API for cryptocurrency trading robots.',
      long_description=readme(),
      url='https://github.com/bmpenuelas/OrbBit',
      author='The best people.',
      author_email='bmpenuelas@gmail.com',
      license='Closed source',
      packages=['orbbit'],
      install_requires=[
          'datetime',
      ],
      zip_safe=False)