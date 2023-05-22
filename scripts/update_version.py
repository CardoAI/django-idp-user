import re

# Read the __init__.py file to find the __version__ value
with open('idp_user/__init__.py', 'r') as init_file:
    init_content = init_file.read()
    version_match = re.search(r'__version__ = "(\d+\.\d+\.\d+)"', init_content)
    if version_match:
        version = version_match.group(1)
    else:
        version = None

# Replace the version value in the README.md file
if version:
    with open('README.md', 'r+') as readme_file:
        readme_content = readme_file.read()
        updated_content = re.sub(r'\[pypi-badge\]: https://img.shields.io/badge/version-(.+?)-blue', f'[pypi-badge]: https://img.shields.io/badge/version-{version}-blue', readme_content)

        if updated_content != readme_content:
            readme_file.seek(0)
            readme_file.write(updated_content)
            readme_file.truncate()
            print('Version replaced successfully in README.md')
            print('Updated content in README.md:')
            print(updated_content)
        else:
            print('Version in README.md is already up to date')
else:
    print('Unable to find __version__ value in idp_user/__init__.py')
