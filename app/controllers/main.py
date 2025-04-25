# app/controllers/main.py  (versão 25-abr-2025)

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, jsonify, current_app, send_file
)
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
import calendar, logging, os

from app import db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import (
    RegistroPontoForm, EditarPontoForm,
    RegistroAfastamentoForm, AtividadeForm
)
from app.utils.helpers import get_usuario_contexto, calcular_horas   # <- helpers que já existiam

logger = logging.getLogger(__name__)
main   = Blueprint("main", __name__)

# ----------------------------------------------------------------------
# REGISTRAR PONTO
# ----------------------------------------------------------------------
@main.route("/registrar-ponto", methods=["GET", "POST"])
@login_required
def registrar_ponto():
    form = RegistroPontoForm()

    if request.method == "GET":
        data_query = request.args.get("data")
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash("Data URL inválida.", "warning")

    if form.validate_on_submit():
        try:
            data_sel = form.data.data
            existente = Ponto.query.filter_by(
                user_id=current_user.id, data=data_sel
            ).first()
            if existente:
                flash("Registro já existe.", "danger")
                return redirect(
                    url_for("main.editar_ponto", ponto_id=existente.id)
                )

            horas = calcular_horas(
                data_sel,
                form.entrada.data, form.saida.data,
                form.saida_almoco.data, form.retorno_almoco.data
            )

            novo = Ponto(
                user_id=current_user.id,
                data=data_sel,
                entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data,
                retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data,
                horas_trabalhadas=horas,
                observacoes=form.observacoes.data,
                afastamento=False,
                tipo_afastamento=None
            )
            db.session.add(novo)
            db.session.flush()           # garante ID

            if form.atividades.data and form.atividades.data.strip():
                db.session.add(
                    Atividade(
                        ponto_id=novo.id,
                        descricao=form.atividades.data.strip()
                    )
                )

            db.session.commit()
            flash("Registro criado!", "success")
            return redirect(
                url_for("main.dashboard",
                        mes=data_sel.month, ano=data_sel.year)
            )

        except Exception as e:
            logger.error(f"Erro reg ponto: {e}", exc_info=True)
            db.session.rollback()
            flash("Erro inesperado.", "danger")

    return render_template("main/registrar_ponto.html",
                           form=form, title="Registrar Ponto")

# ----------------------------------------------------------------------
# EDITAR PONTO  (… código inalterado …)
# ----------------------------------------------------------------------
@main.route("/editar-ponto/<int:ponto_id>", methods=["GET", "POST"])
@login_required
def editar_ponto(ponto_id):
    # … (manteve-se igual ao original, sem ; else :) …
    # ------------------------------------------------------------------

# ----------------------------------------------------------------------
# REGISTRAR AFASTAMENTO (… código inalterado …)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# RELATÓRIO MENSAL  (HTML)
# ----------------------------------------------------------------------
@main.route("/relatorio-mensal")
@login_required
def relatorio_mensal():
    # … (código inalterado) …
    # ------------------------------------------------------------------

# ----------------------------------------------------------------------
# RELATÓRIO MENSAL – PDF
# ----------------------------------------------------------------------
@main.route("/relatorio-mensal/pdf")
@login_required
def relatorio_mensal_pdf():
    user_id_req  = request.args.get("user_id", type=int)
    usuario_alvo = current_user

    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
            flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
            return redirect(request.referrer or url_for("main.dashboard"))

    hoje = date.today()
    mes  = request.args.get("mes", default=hoje.month, type=int)
    ano  = request.args.get("ano", default=hoje.year,  type=int)

    try:
        from app.utils.export import generate_pdf
        rel_path = generate_pdf(usuario_alvo.id, mes, ano)

        if rel_path:
            abs_path = os.path.join(current_app.static_folder, rel_path)
            if os.path.exists(abs_path):
                nome_mes = datetime(ano, mes, 1).strftime("%B").lower()
                fname    = f\"relatorio_{usuario_alvo.matricula}_{nome_mes}_{ano}.pdf\"
                return send_file(abs_path, as_attachment=True,
                                 download_name=fname)
            else:
                logger.error(\"PDF não encontrado: %s\", abs_path)
                flash(\"Erro: PDF não encontrado.\", "danger")
        else:
            flash(\"Erro ao gerar PDF.\", "danger")

    except Exception as e:
        logger.error(\"Erro gerar/enviar PDF: %s\", e, exc_info=True)
        flash(\"Erro inesperado ao gerar PDF.\", "danger")

    return redirect(request.referrer or
                    url_for("main.relatorio_mensal",
                            user_id=usuario_alvo.id, mes=mes, ano=ano))

# ----------------------------------------------------------------------
# RELATÓRIO MENSAL – EXCEL   <<< BLOCO CORRIGIDO
# ----------------------------------------------------------------------
@main.route("/relatorio-mensal/excel")
@login_required
def relatorio_mensal_excel():
    user_id_req  = request.args.get("user_id", type=int)
    usuario_alvo = current_user

    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
            flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
            return redirect(request.referrer or url_for("main.dashboard"))

    hoje = date.today()
    mes  = request.args.get("mes", default=hoje.month, type=int)
    ano  = request.args.get("ano", default=hoje.year,  type=int)

    try:
        from app.utils.export import generate_excel
        rel_path = generate_excel(usuario_alvo.id, mes, ano)

        if rel_path:
            abs_path = os.path.join(current_app.static_folder, rel_path)
            if os.path.exists(abs_path):
                nome_mes = datetime(ano, mes, 1).strftime("%B").lower()
                fname    = (f\"relatorio_{usuario_alvo.matricula}_\"
                            f\"{nome_mes}_{ano}.xlsx\")
                return send_file(
                    abs_path, as_attachment=True, download_name=fname,
                    mimetype=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\"
                )
            else:
                logger.error(\"Excel não encontrado: %s\", abs_path)
                flash(\"Erro: Excel não encontrado.\", "danger")
        else:
            flash(\"Erro ao gerar Excel.\", "danger")

    except Exception as e:
        logger.error(\"Erro gerar/enviar Excel: %s\", e, exc_info=True)
        flash(\"Erro inesperado ao gerar Excel.\", "danger")

    return redirect(request.referrer or
                    url_for("main.relatorio_mensal",
                            user_id=usuario_alvo.id, mes=mes, ano=ano))

# ----------------------------------------------------------------------
# VISUALIZAR/EXCLUIR/ETC.  (restante do arquivo continua igual,
# sem nenhum 'if … ; else :' ou '… ; try:' )
# ----------------------------------------------------------------------
