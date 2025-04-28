from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import calendar
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app import db
from datetime import datetime, date, timedelta, time
import logging
import os
import tempfile
import pandas as pd

main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# ... (Funções auxiliares get_usuario_contexto e calcular_horas mantidas) ...
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    if not entrada or not saida: return None
    try:
        entrada_dt = datetime.combine(data_ref, entrada); saida_dt = datetime.combine(data_ref, saida)
        if saida_dt < entrada_dt: saida_dt += timedelta(days=1)
        diff_total = saida_dt - entrada_dt; horas_trabalhadas = diff_total.total_seconds() / 3600
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco); retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)
            if retorno_almoco_dt < saida_almoco_dt: retorno_almoco_dt += timedelta(days=1)
            diff_almoco = retorno_almoco_dt - saida_almoco_dt; horas_trabalhadas -= diff_almoco.total_seconds() / 3600
        return max(0, horas_trabalhadas)
    except Exception as e: logger.error(f"Erro calc horas {data_ref}: {e}", exc_info=True); return None

def get_usuario_contexto():
    user_id_req = request.args.get('user_id', type=int); usuario_selecionado = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_selecionado = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

@main.route('/')
@login_required
def index(): return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    # ... (Código mantido) ...
    usuario_ctx, usuarios_admin = get_usuario_contexto(); hoje = date.today()
    mes_req = request.args.get('mes', default=hoje.month, type=int); ano_req = request.args.get('ano', default=hoje.year, type=int)
    try:
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano_req, mes_req, 1); num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]; ultimo_dia = date(ano_req, mes_req, num_dias_mes)
        registros = Ponto.query.filter(Ponto.user_id == usuario_ctx.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data.desc()).all()
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all(); feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0; registros_dict = {r.data: r for r in registros}
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_dict.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req); proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)
        return render_template('main/dashboard.html', registros=registros, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes, dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, usuario=usuario_ctx, usuarios=usuarios_admin, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano)
    except ValueError: flash('Data inválida.', 'danger'); return redirect(url_for('main.dashboard'))
    except Exception as e: logger.error(f"Erro dashboard: {e}", exc_info=True); flash('Erro ao carregar dashboard.', 'danger'); hoje = date.today(); return render_template('main/dashboard.html', registros=[], mes_atual=hoje.month, ano_atual=hoje.year, nome_mes="Mês Atual", dias_uteis=0, dias_trabalhados=0, dias_afastamento=0, horas_trabalhadas=0, carga_horaria_devida=0, saldo_horas=0, media_diaria=0, usuario=current_user, usuarios=None)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Registra ponto para um dia específico."""
    form = RegistroPontoForm()
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try: form.data.data = date.fromisoformat(data_query)
            except ValueError: flash('Data URL inválida.', 'warning')

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                flash(f'Registro para {data_selecionada.strftime("%d/%m/%Y")} já existe.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            horas_calculadas = calcular_horas(data_selecionada, form.entrada.data, form.saida.data, form.saida_almoco.data, form.retorno_almoco.data)
            novo_registro = Ponto(
                user_id=current_user.id, data=data_selecionada, entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data, retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data, horas_trabalhadas=horas_calculadas,
                observacoes=form.observacoes.data,
                # --- SALVANDO NOVO CAMPO ---
                resultados_produtos=form.resultados_produtos.data,
                # -------------------------
                afastamento=False, tipo_afastamento=None
            )
            db.session.add(novo_registro)
            db.session.flush() # Para obter o ID

            if form.atividades.data and form.atividades.data.strip():
                atividade = Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip())
                db.session.add(atividade)

            db.session.commit()
            flash('Registro criado!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro reg ponto: {e}", exc_info=True)
            flash('Erro ao registrar.', 'danger')
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")


@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id): # Assinatura corrigida
    """Edita um registro de ponto existente."""
    registro = Ponto.query.get_or_404(ponto_id)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Permissão negada.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = EditarPontoForm(obj=registro) # Preenche com dados existentes
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    # Preenche campos de texto no GET se não houver dados de erro de validação anterior
    if request.method == 'GET':
        if atividade_existente and not form.atividades.data:
            form.atividades.data = atividade_existente.descricao
        # obj=registro já preenche resultados_produtos e observacoes se existirem no modelo

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            if is_afastamento and not tipo_afastamento:
                 flash('Selecione Tipo Afastamento.', 'danger')
                 return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

            # Atualiza o registro principal
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            # --- ATUALIZANDO NOVO CAMPO ---
            registro.resultados_produtos = form.resultados_produtos.data
            # ----------------------------

            if is_afastamento:
                registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else:
                registro.entrada=form.entrada.data
                registro.saida_almoco=form.saida_almoco.data
                registro.retorno_almoco=form.retorno_almoco.data
                registro.saida=form.saida.data
                registro.horas_trabalhadas = calcular_horas(data_selecionada, form.entrada.data, form.saida.data, form.saida_almoco.data, form.retorno_almoco.data)

            # Atualiza/Cria/Deleta atividade
            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                if atividade_existente: atividade_existente.descricao = descricao_atividade
                else: db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade))
            elif atividade_existente:
                 db.session.delete(atividade_existente)

            db.session.commit()
            flash('Registro atualizado!', 'success')
            return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro edit ponto {ponto_id}: {e}", exc_info=True)
            flash('Erro ao atualizar.', 'danger')
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    form = RegistroAfastamentoForm();
    if request.method == 'GET': data_query = request.args.get('data');
    if data_query: try: form.data.data = date.fromisoformat(data_query); except ValueError: flash('Data URL inválida.', 'warning')
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data; tipo_afastamento = form.tipo_afastamento.data; registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente: flash(f'Registro para {data_selecionada.strftime("%d/%m/%Y")} já existe.', 'danger'); return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
            novo_afastamento = Ponto(user_id=current_user.id, data=data_selecionada, afastamento=True, tipo_afastamento=tipo_afastamento, entrada=None, saida_almoco=None, retorno_almoco=None, saida=None, horas_trabalhadas=None, observacoes=None, resultados_produtos=None) # Adicionado resultados_produtos=None
            db.session.add(novo_afastamento); db.session.commit(); flash('Afastamento registrado!', 'success'); return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e: db.session.rollback(); logger.error(f"Erro reg afastamento: {e}", exc_info=True); flash('Erro ao registrar.', 'danger')
    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")

@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias(): flash('Use "Registrar Afastamento".', 'info'); return redirect(url_for('main.registrar_afastamento', **request.args))

@main.route('/calendario')
@login_required
def calendario():
    # ... (código mantido) ...
    usuario_ctx, usuarios_admin = get_usuario_contexto(); hoje = date.today(); mes_req = request.args.get('mes', default=hoje.month, type=int); ano_req = request.args.get('ano', default=hoje.year, type=int)
    try:
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano_req, mes_req, 1); num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]; ultimo_dia = date(ano_req, mes_req, num_dias_mes)
        registros = Ponto.query.filter(Ponto.user_id == usuario_ctx.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).all(); registros_dict = {r.data: r for r in registros}
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all(); feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_dict.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req); proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)
        cal = calendar.Calendar(firstweekday=6); semanas_mes = cal.monthdayscalendar(ano_req, mes_req); calendario_data = []
        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                dia_info = {'dia': dia, 'data': None, 'is_mes_atual': False, 'registro': None, 'feriado': None, 'is_hoje': False, 'is_fim_semana': False}
                if dia != 0: data_atual = date(ano_req, mes_req, dia); dia_info.update({'data': data_atual, 'is_mes_atual': True, 'registro': registros_dict.get(data_atual), 'feriado': feriados_dict.get(data_atual), 'is_hoje': (data_atual == hoje), 'is_fim_semana': (data_atual.weekday() >= 5)})
                semana_data.append(dia_info)
            calendario_data.append(semana_data)
        return render_template('main/calendario.html', calendario_data=calendario_data, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes, dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, usuario=usuario_ctx, usuarios=usuarios_admin, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano)
    except ValueError: flash('Data inválida.', 'danger'); return redirect(url_for('main.dashboard'))
    except Exception as e: logger.error(f"Erro calendário: {e}", exc_info=True); flash('Erro ao carregar calendário.', 'danger'); return redirect(url_for('main.dashboard'))

@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    # ... (código mantido) ...
    usuario_ctx, usuarios_admin = get_usuario_contexto(); hoje = date.today(); mes_req = request.args.get('mes', default=hoje.month, type=int); ano_req = request.args.get('ano', default=hoje.year, type=int)
    try:
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano_req, mes_req, 1); num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]; ultimo_dia = date(ano_req, mes_req, num_dias_mes)
        registros = Ponto.query.filter(Ponto.user_id == usuario_ctx.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data).all()
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all(); feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        registros_por_data = {registro.data: registro for registro in registros}; ponto_ids = [r.id for r in registros]; atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all(); atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto: atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_por_data.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req); proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)
        return render_template('main/relatorio_mensal.html', registros=registros, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano, dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, feriados_dict=feriados_dict, feriados_datas=feriados_datas, registros_por_data=registros_por_data, atividades_por_ponto=atividades_por_ponto, usuario=usuario_ctx, usuarios=usuarios_admin, date=date, ultimo_dia=ultimo_dia, ano=ano_req, mes=mes_req)
    except ValueError: flash('Data inválida.', 'danger'); return redirect(url_for('main.dashboard'))
    except Exception as e: logger.error(f"Erro relatório mensal: {e}", exc_info=True); flash('Erro ao gerar relatório.', 'danger'); return redirect(url_for('main.dashboard'))

@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    # ... (código mantido) ...
    user_id_req = request.args.get('user_id', type=int); usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_pdf; pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano)
        if pdf_rel_path: pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path);
        if os.path.exists(pdf_abs_path): nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower(); download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"; return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
        else: logger.error(f"PDF não encontrado: {pdf_abs_path}"); flash('Erro: PDF não encontrado.', 'danger')
        else: flash('Erro ao gerar PDF.', 'danger')
    except Exception as e: logger.error(f"Erro gerar/enviar PDF: {e}", exc_info=True); flash('Erro inesperado ao gerar PDF.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    # ... (código mantido) ...
    user_id_req = request.args.get('user_id', type=int); usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_excel; excel_rel_path = generate_excel(usuario_alvo.id, mes, ano)
        if excel_rel_path: excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path);
        if os.path.exists(excel_abs_path): nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower(); download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"; return send_file(excel_abs_path, as_attachment=True, download_name=download_name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else: logger.error(f"Excel não encontrado: {excel_abs_path}"); flash('Erro: Excel não encontrado.', 'danger')
        else: flash('Erro ao gerar Excel.', 'danger')
    except Exception as e: logger.error(f"Erro gerar/enviar Excel: {e}", exc_info=True); flash('Erro inesperado ao gerar Excel.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id): # Assinatura corrigida
    # ... (código mantido) ...
    registro = Ponto.query.get_or_404(ponto_id);
    if registro.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all(); usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono: flash('Usuário não encontrado.', 'danger'); return redirect(url_for('main.dashboard'))
    return render_template('main/visualizar_ponto.html', registro=registro, atividades=atividades, usuario=usuario_dono, title="Visualizar Registro")

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id): # Assinatura corrigida
    # ... (código mantido) ...
    registro = Ponto.query.get_or_404(ponto_id); data_registro = registro.data
    if registro.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    try: db.session.delete(registro); db.session.commit(); flash('Registro excluído!', 'success')
    except Exception as e: db.session.rollback(); logger.error(f"Erro excluir ponto {ponto_id}: {e}", exc_info=True); flash('Erro ao excluir.', 'danger')
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

@main.route('/perfil')
@login_required
def perfil():
    # ... (código mantido) ...
    usuario_atualizado = User.query.get(current_user.id);
    if not usuario_atualizado: flash('Erro ao carregar perfil.', 'danger'); return redirect(url_for('main.dashboard'))
    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Registra múltiplos pontos de uma vez."""
    form = MultiploPontoForm() # Usa o form minimalista para CSRF
    if form.validate_on_submit(): # Valida CSRF e processa POST
        try:
            datas_str = request.form.getlist('datas[]')
            entradas_str = request.form.getlist('entradas[]')
            saidas_almoco_str = request.form.getlist('saidas_almoco[]')
            retornos_almoco_str = request.form.getlist('retornos_almoco[]')
            saidas_str = request.form.getlist('saidas[]')
            atividades_desc = request.form.getlist('atividades[]')
            # --- LER NOVOS CAMPOS ---
            resultados_produtos_desc = request.form.getlist('resultados_produtos[]')
            observacoes_desc = request.form.getlist('observacoes[]')
            # -------------------------

            registros_criados, registros_ignorados = 0, 0
            datas_processadas = set()

            for i in range(len(datas_str)):
                data_str = datas_str[i]
                if not data_str: continue
                try: data = date.fromisoformat(data_str)
                except ValueError: flash(f'Data inválida: {data_str}', 'warning'); continue
                if data in datas_processadas: continue
                datas_processadas.add(data)
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente: flash(f'Registro {data.strftime("%d/%m/%Y")} já existe.', 'info'); registros_ignorados += 1; continue

                entrada_str = entradas_str[i] if i < len(entradas_str) else None
                saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None
                retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None
                saida_str_i = saidas_str[i] if i < len(saidas_str) else None
                atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None
                # --- OBTER DADOS DOS NOVOS CAMPOS ---
                resultado_desc_i = resultados_produtos_desc[i].strip() if i < len(resultados_produtos_desc) and resultados_produtos_desc[i] else None
                observacao_i = observacoes_desc[i].strip() if i < len(observacoes_desc) and observacoes_desc[i] else None
                # -----------------------------------

                try:
                    entrada_t = time.fromisoformat(entrada_str) if entrada_str else None
                    saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None
                    retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None
                    saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError: flash(f'Hora inválida {data.strftime("%d/%m/%Y")}.', 'warning'); continue

                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)
                novo_registro = Ponto(
                    user_id=current_user.id, data=data, entrada=entrada_t,
                    saida_almoco=saida_almoco_t, retorno_almoco=retorno_almoco_t,
                    saida=saida_t, horas_trabalhadas=horas_calculadas,
                    afastamento=False, tipo_afastamento=None,
                    # --- SALVAR NOVOS CAMPOS ---
                    resultados_produtos=resultado_desc_i,
                    observacoes=observacao_i
                    # -------------------------
                )
                db.session.add(novo_registro)
                try:
                    db.session.flush()
                    if atividade_desc_i: db.session.add(Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i))
                    db.session.commit(); registros_criados += 1
                except Exception as commit_err: db.session.rollback(); logger.error(f"Erro salvar reg/atv {data}: {commit_err}", exc_info=True); flash(f'Erro ao salvar {data.strftime("%d/%m/%Y")}.', 'danger')

            # Mensagens de feedback
            if registros_criados > 0 and registros_ignorados == 0: flash(f'{registros_criados} registro(s) criado(s)!', 'success')
            elif registros_criados > 0 and registros_ignorados > 0: flash(f'{registros_criados} criado(s). {registros_ignorados} ignorado(s).', 'warning')
            elif registros_ignorados > 0 and registros_criados == 0: flash('Nenhum novo registro criado (datas já existiam).', 'info')
            elif len(datas_processadas) == 0: flash('Nenhuma data válida informada.', 'warning')
            else: flash('Nenhum registro criado devido a erros.', 'danger')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar múltiplos pontos: {e}", exc_info=True)
            flash('Erro inesperado ao processar registros.', 'danger')
            return redirect(url_for('main.registrar_multiplo_ponto'))

    # Se GET ou validação CSRF falhar
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos")


@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id): # Assinatura corrigida
    """Registra ou edita a atividade de um ponto específico."""
    ponto = Ponto.query.get_or_404(ponto_id)
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Permissão negada.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = AtividadeForm() # Usa o WTForm
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    if form.validate_on_submit(): # Processa POST usando WTForms
        try:
            descricao = form.descricao.data.strip()
            if atividade_existente:
                atividade_existente.descricao = descricao
            else:
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao)
                db.session.add(nova_atividade)
            db.session.commit()
            flash('Atividade salva!', 'success')
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro salvar atividade {ponto_id}: {e}", exc_info=True)
            flash('Erro ao salvar atividade.', 'danger')

    elif request.method == 'GET': # Preenche o form no GET
        if atividade_existente:
            form.descricao.data = atividade_existente.descricao

    # Renderiza o template passando o form
    return render_template('main/registrar_atividade.html',
                           ponto=ponto,
                           form=form, # Passa o objeto form
                           title="Registrar/Editar Atividade")

