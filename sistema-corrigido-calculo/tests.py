import unittest
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from datetime import datetime, date, time, timedelta

class TestPontoEletronico(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Criar usuário de teste
        self.user = User(
            name='Usuário Teste',
            email='teste@example.com',
            matricula='TEST001',
            vinculo='SENAPPEN - Teste'
        )
        self.user.set_password('senha123')
        db.session.add(self.user)
        db.session.commit()
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        
    def test_user_creation(self):
        """Testa a criação de usuário"""
        user = User.query.filter_by(email='teste@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Usuário Teste')
        self.assertEqual(user.matricula, 'TEST001')
        self.assertTrue(user.check_password('senha123'))
        
    def test_registro_ponto(self):
        """Testa o registro de ponto e cálculo de horas"""
        hoje = date.today()
        
        # Criar registro de ponto
        ponto = Ponto(
            user_id=self.user.id,
            data=hoje,
            entrada=time(8, 0),
            saida_almoco=time(12, 0),
            retorno_almoco=time(13, 0),
            saida=time(17, 0)
        )
        
        # Calcular horas trabalhadas
        t1 = datetime.combine(hoje, ponto.saida_almoco) - datetime.combine(hoje, ponto.entrada)
        t2 = datetime.combine(hoje, ponto.saida) - datetime.combine(hoje, ponto.retorno_almoco)
        total_segundos = t1.total_seconds() + t2.total_seconds()
        ponto.horas_trabalhadas = total_segundos / 3600
        
        db.session.add(ponto)
        db.session.commit()
        
        # Verificar registro
        ponto_salvo = Ponto.query.filter_by(user_id=self.user.id, data=hoje).first()
        self.assertIsNotNone(ponto_salvo)
        self.assertEqual(ponto_salvo.entrada, time(8, 0))
        self.assertEqual(ponto_salvo.saida, time(17, 0))
        self.assertEqual(ponto_salvo.horas_trabalhadas, 8.0)
        
    def test_registro_atividade(self):
        """Testa o registro de atividades"""
        hoje = date.today()
        
        # Criar registro de ponto
        ponto = Ponto(user_id=self.user.id, data=hoje)
        db.session.add(ponto)
        db.session.commit()
        
        # Adicionar atividade
        atividade = Atividade(
            ponto_id=ponto.id,
            descricao='Teste de atividade realizada'
        )
        db.session.add(atividade)
        db.session.commit()
        
        # Verificar atividade
        atividades = Atividade.query.filter_by(ponto_id=ponto.id).all()
        self.assertEqual(len(atividades), 1)
        self.assertEqual(atividades[0].descricao, 'Teste de atividade realizada')
        
    def test_calculo_banco_horas(self):
        """Testa o cálculo do banco de horas"""
        hoje = date.today()
        
        # Criar feriado
        feriado = Feriado(
            data=hoje + timedelta(days=1),
            descricao='Feriado de Teste'
        )
        db.session.add(feriado)
        
        # Criar registros de ponto para 5 dias (uma semana de trabalho)
        for i in range(5):
            data = hoje - timedelta(days=i)
            # Pular se for fim de semana
            if data.weekday() >= 5:
                continue
                
            # Criar registro com 8 horas em alguns dias e 9 em outros (1h extra)
            horas = 8 if i % 2 == 0 else 9
            
            ponto = Ponto(
                user_id=self.user.id,
                data=data,
                entrada=time(8, 0),
                saida_almoco=time(12, 0),
                retorno_almoco=time(13, 0),
                saida=time(16 + horas - 8, 0),  # 16h para 8h, 17h para 9h
                horas_trabalhadas=horas
            )
            db.session.add(ponto)
        
        db.session.commit()
        
        # Verificar registros
        registros = Ponto.query.filter_by(user_id=self.user.id).all()
        self.assertGreater(len(registros), 0)
        
        # Calcular saldo de horas
        total_horas = sum(r.horas_trabalhadas for r in registros if r.horas_trabalhadas)
        dias_uteis = len(registros)
        horas_esperadas = dias_uteis * 8
        saldo_horas = total_horas - horas_esperadas
        
        # Verificar se o saldo está correto (deve haver horas extras)
        self.assertGreaterEqual(saldo_horas, 0)
        
if __name__ == '__main__':
    unittest.main()
