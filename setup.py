# encoding=utf-8

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='flask-halalchemy',
    version='0.1-dev',
    url='https://github.com/jokull/flask-halalchemy',
    license='BSD',
    author='Jokull Solberg Audunsson',
    author_email='jokull@solberg.is',
    description='Expose Flask-SQLAlchemy models as json+hal resources',
    long_description=open('README.md').read(),
    classifiers=[
        # 'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=['flask_halalchemy'],
    include_package_data=True,
    zip_safe=False,
    platforms='any'
)
