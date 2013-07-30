from distutils.core import setup

setup(
    name='RemoteDiff',
    version='0.1dev',
    description='Check filesystem/ownership/permission/size differences in remote/local paths.',
    author='Sury Prakash Soni',
    author_email='suryasoni@gmail.com',
    url='https://github.com/spsoni/remotediff',
    packages=['remotediff',],
    license='MIT License',
    long_description=open('README.txt').read(),
)
