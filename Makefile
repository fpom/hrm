upload:
	rm -rf dist
	python -m build --sdist
	python -m twine upload dist/*

clean:
	rm -rf build dist *.egg-info pdf __pycache__

test:
	python hrm_tests.py
