.PHONY: test backtest all

test:
	python test_period_engine.py
	python test_manual.py

backtest:
	python backtest.py

all: test backtest
