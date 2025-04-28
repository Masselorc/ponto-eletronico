# ... (outras importações e código) ...
from app.models.relatorio_completo import RelatorioMensalCompleto # Certifique-se que está importado

# ... (código das outras rotas) ...

# --- NOVA ROTA: Visualizar Relatório Completo em HTML ---
@main.route('/visualizar-relatorio-completo')
@login_required
def visualizar_relatorio_completo():
    """Exibe o relatório completo salvo em formato HTML."""
    try:
        # Tenta obter user_id, mes e ano da URL
        user_id = request.args.get('user_id', type=int)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not user_id or not mes or not ano:
            flash("Informações insuficientes para visualizar o relatório (usuário, mês ou ano ausente).", 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        # Verifica permissão (usuário só pode ver o seu, admin pode qualquer um)
        if user_id != current_user.id and not current_user.is_admin:
            flash("Você não tem permissão para visualizar este relatório.", 'danger')
            return redirect(url_for('main.dashboard'))

        # Busca o relatório completo salvo no banco
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=user_id, ano=ano, mes=mes
        ).first()

        if not relatorio_salvo:
            flash("Nenhum relatório completo salvo encontrado para este período.", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        # Busca os dados base do relatório mensal
        dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)

        # Cria o contexto completo para o template HTML
        contexto_completo = {
            **dados_relatorio_base,
            'autoavaliacao_data': relatorio_salvo.autoavaliacao,
            'dificuldades_data': relatorio_salvo.dificuldades,
            'sugestoes_data': relatorio_salvo.sugestoes,
            'declaracao_marcada': relatorio_salvo.declaracao_marcada,
            'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y %H:%M:%S'), # Usa data da última atualização
            'titulo': f'Relatório de Produtividade Mensal - {dados_relatorio_base["nome_mes"]}/{ano}' # Título para a página HTML
        }

        # Renderiza o novo template HTML
        return render_template('main/visualizar_relatorio_completo.html', **contexto_completo)

    except ValueError as ve:
        logger.error(f"ValueError ao visualizar relatório completo: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para visualização: {ve}.", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao visualizar relatório completo: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao visualizar o relatório completo.', 'danger')

    # Redireciona de volta para a página do relatório mensal em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))
# --- FIM DA NOVA ROTA ---

# ... (restante do código do controller) ...

