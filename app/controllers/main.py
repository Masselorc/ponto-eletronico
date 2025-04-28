# -*- coding: utf-8 -*-
# Importações básicas e de bibliotecas padrão
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import calendar
import logging
import os
import tempfile
import pandas as pd
from datetime import datetime, date, timedelta, time
from sqlalchemy import desc

# --- Definição do Blueprint 'main' DEVE ESTAR AQUI ---
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# --- FIM DA DEFINIÇÃO ---

# Importações de módulos da aplicação (DEPOIS DA DEFINIÇÃO DO BLUEPRINT)
from app import db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.models.relatorio_completo import RelatorioMensalCompleto
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app.forms.relatorio import RelatorioCompletoForm

# ... (Restante do código das funções e rotas) ...

@main.route('/') # A rota raiz
@login_required
def index():
    """Redireciona para o dashboard."""
    # Esta função simplesmente redireciona, não deve causar o TypeError por si só
    # se chamada em um contexto de requisição normal.
    return redirect(url_for('main.dashboard'))

# ... (Restante das rotas) ...
