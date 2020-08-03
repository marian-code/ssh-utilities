python setup.py sdist bdist_wheel
rm dist/*
twine upload dist/*