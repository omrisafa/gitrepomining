from setuptools import setup, find_packages

with open('requirement.txt') as reqs_file:
    requirements = reqs_file.read().splitlines()

with open('test-requirements.txt') as reqs_file:
    test_requirements = reqs_file.read().splitlines()

long_description = 'pygitminer is a Python framework for Git Repository Mining.'

setup(
    name='pygitminer',
    description='Python Framework for Git Repository Mining',
    long_description=long_description,
    author='Safa Omri',
    author_email='safa.omri@kit.edu',
    version='1.15',
    packages=find_packages('.'),
    url='https://github.com/omrisafa/gitrepomining',
    license='Apache License',
    package_dir={'pygitminer': 'pygitminer'},
    python_requires='>=3.5',
    install_requires=requirements,
    test_requirements=requirements + test_requirements,
    classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
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
