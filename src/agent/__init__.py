"""
Agente que responde perguntas em linguagem natural sobre os dados da API.

O LLM só escolhe ferramentas de leitura (src/agent/ferramentas.py); quem
consulta o banco é o nosso código, com filtros validados e limite de linhas.
"""
