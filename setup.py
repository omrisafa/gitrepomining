from setuptools import setup, find_packages

with open('requirement.txt') as reqs_file:
    requirements = reqs_file.read().splitlines()

setup(
    name='pygitminer',
    description='Git Repository Mining: a Python Framework',
    author='Safa Omri',
    author_email='safa.omri@kit.edu',
    version='1.15',
    packages=find_packages('.'),
    url='https://github.com/omrisafa/gitrepomining',
    package_dir={'pygitminer': 'pygitminer'},
    python_requires='>=3.5',
    install_requires=requirements,
    classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Research',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Topic :: Software Development :: Libraries :: Python Modules',
            "Operating System :: OS Independent",
            "Operating System :: POSIX",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: MacOS :: MacOS X",
            ]
)
