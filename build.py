#!/usr/bin/env python3
import py_compile
import shutil
import os

def build_protected_package():
    # Create dist directory structure
    os.makedirs('dist/alf_AIdebugger', exist_ok=True)
    
    # Compile the Python files to bytecode
    py_compile.compile('src/alf_AIdebugger/cli.py', 
                      'dist/alf_AIdebugger/cli.pyc')
    py_compile.compile('src/alf_AIdebugger/__init__.py',
                      'dist/alf_AIdebugger/__init__.pyc')
    
    # Create setup files
    with open('dist/setup.py', 'w') as f:
        f.write('''
from setuptools import setup

setup(
    name="alf_AIdebugger",
    version="0.1.0",
    packages=['alf_AIdebugger'],
    package_data={'alf_AIdebugger': ['*.pyc']},
    exclude_package_data={'': ['*.py']},
    install_requires=[
        'openai>=1.0.0',
        'rich>=10.0.0',
    ],
    entry_points={
        'console_scripts': [
            'alf-debug=alf_AIdebugger.cli:main',
        ],
    },
)
''')

    # Create minimal README
    with open('dist/README.md', 'w') as f:
        f.write('''
# alf_AIdebugger

An AI-powered debugger using SambaNova's API.

## Installation

```bash
pip install alf_AIdebugger
```

## Usage

1. Set your SambaNova API key:
```bash
export SAMBANOVA_API_KEY=your_api_key_here
```

2. Run the debugger:
```bash
alf-debug
```
''')

if __name__ == '__main__':
    build_protected_package()