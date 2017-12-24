
# To setup this package, issue "pip install -e ."

from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='orbbit',
      version='0.1',
      description='A language-independent API for cryptocurrency trading robots.',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
      ],
      keywords='cryptocurrency trading robots',
      url='https://github.com/bmpenuelas/OrbBit',
      author='The best people.',
      author_email='bmpenuelas@gmail.com',
      license='Closed source',
      packages=['orbbit'],
      include_package_data=True,
      install_requires=[
          'pandas',
          'ccxt',
          'flask',
          'flask_httpauth',
          'pymongo',
          'matplotlib',
      ],
      # scripts=['bin/start_hi'],
      # entry_points={
      #     'console_scripts': [
      #         'start_main = my_project.__main__:main'
      #     ]
      # },
      zip_safe=False)