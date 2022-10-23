from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


def requirements():
    with open('requirements.txt') as f:
        return f.read().splitlines()


def version():
    with open('toolbox_runner/__version__.py') as f:
        loc = dict()
        exec(f.read(), loc, loc)
        return loc['__version__']


setup(
    name='toolbox_runner',
    author='Mirko Mälicke',
    author_email='mirko@hydrocode.de',
    description='Run data processing tools from docker containers from Python',
    long_description=readme(),
    long_description_content_type='text/markdown',
    license='MIT',
    version=version(),
    packages=find_packages(),
    install_requires=requirements()
)
