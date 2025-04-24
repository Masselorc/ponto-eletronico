"""
Módulo de utilitários para tratamento de erros na aplicação.
"""

import logging
import traceback
from functools import wraps
from flask import flash, redirect, url_for, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

logger = logging.getLogger(__name__)

def handle_errors(route_function):
    """
    Decorador para tratar erros em rotas.
    
    Args:
        route_function: A função de rota a ser decorada
        
    Returns:
        A função decorada com tratamento de erros
    """
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        try:
            return route_function(*args, **kwargs)
        except SQLAlchemyError as e:
            # Erro de banco de dados
            from app import db
            db.session.rollback()
            error_msg = str(e)
            logger.error(f"Erro de banco de dados: {error_msg}")
            logger.error(traceback.format_exc())
            flash(f"Erro de banco de dados. Por favor, tente novamente mais tarde.", "danger")
            return redirect(url_for('main.dashboard'))
        except IntegrityError as e:
            # Erro de integridade (violação de chave única, etc.)
            from app import db
            db.session.rollback()
            error_msg = str(e)
            logger.error(f"Erro de integridade: {error_msg}")
            logger.error(traceback.format_exc())
            flash(f"Erro de integridade de dados. Verifique se os dados informados são válidos.", "danger")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            # Erro genérico
            error_msg = str(e)
            logger.error(f"Erro não tratado: {error_msg}")
            logger.error(traceback.format_exc())
            flash(f"Ocorreu um erro inesperado. Por favor, tente novamente mais tarde.", "danger")
            return redirect(url_for('main.dashboard'))
    return wrapper

def validate_input(value, validator, error_message="Valor inválido"):
    """
    Valida uma entrada com base em uma função de validação.
    
    Args:
        value: O valor a ser validado
        validator: Uma função que recebe o valor e retorna True se for válido
        error_message: Mensagem de erro a ser exibida se a validação falhar
        
    Returns:
        bool: True se a validação passar, False caso contrário
        
    Raises:
        ValueError: Se a validação falhar
    """
    if not validator(value):
        raise ValueError(error_message)
    return True

def safe_db_operation(operation):
    """
    Executa uma operação de banco de dados com tratamento de erros.
    
    Args:
        operation: Uma função que executa a operação de banco de dados
        
    Returns:
        O resultado da operação ou None em caso de erro
    """
    try:
        return operation()
    except SQLAlchemyError as e:
        from app import db
        db.session.rollback()
        logger.error(f"Erro de banco de dados: {str(e)}")
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Erro não tratado: {str(e)}")
        logger.error(traceback.format_exc())
        return None
