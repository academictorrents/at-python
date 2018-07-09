init:
	pip install -r requirements.txt
test:
	#python -m pytest -x tests
	python -m pytest -x -s tests
