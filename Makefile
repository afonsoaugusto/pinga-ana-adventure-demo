# Raiz do repo (funciona mesmo se o make for invocado de outro diretório)
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# pyenv: o make costuma herdar PATH enxuto; amplia antes de procurar o binário
PYENV := $(shell \
	PATH="$(HOME)/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:$$PATH"; \
	export PATH; \
	if command -v pyenv >/dev/null 2>&1; then command -v pyenv; \
	elif [ -x "$(HOME)/.pyenv/bin/pyenv" ]; then printf '%s\n' "$(HOME)/.pyenv/bin/pyenv"; \
	elif [ -x /opt/homebrew/bin/pyenv ]; then printf '%s\n' /opt/homebrew/bin/pyenv; \
	elif [ -x /usr/local/bin/pyenv ]; then printf '%s\n' /usr/local/bin/pyenv; \
	else :; fi)

# pyenv costuma expor python3; o nome "python" nem sempre existe na versão ativa
PYTHON := $(PYENV) exec python3

.PHONY: play install _check_pyenv

_check_pyenv:
	@test -n "$(PYENV)" && test -x "$(PYENV)" || { \
		printf '%s\n' "pyenv não encontrado. Ex.: brew install pyenv, ou export PATH com o diretório do pyenv antes de make." >&2; \
		exit 1; \
	}
	@$(PYENV) exec python3 --version >/dev/null 2>&1 || { \
		printf '%s\n' "pyenv: nenhum python3 na versão ativa. No diretório do projeto: pyenv local 3.12 && pyenv install -s" >&2; \
		exit 1; \
	}

# Roda o jogo localmente com o interpretador gerenciado pelo pyenv
play: _check_pyenv
	cd $(ROOT) && $(PYTHON) main.py

# Instala dependências no ambiente ativo do pyenv (uma vez ou após mudanças em requirements.txt)
install: _check_pyenv
	cd $(ROOT) && $(PYTHON) -m pip install -r requirements.txt
