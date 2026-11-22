init:
	pip install -r requirements.txt
test:
	pytest tests -v
test-network:
	pytest tests -v --network --timeout=900

