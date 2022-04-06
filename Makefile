test:
	python hrm_test.py

upload:
	rm -rf dist
	python setup.py sdist
	rm -rf *.egg-info
	twine upload dist/*
