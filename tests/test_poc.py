import sys
import unittest
from pathlib import Path
from io import BytesIO
from dataclasses import replace
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dados import carregar, validar
from modelo import avaliar, Parametros
from streamlit.testing.v1 import AppTest

class ModeloTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conteudo=(ROOT/'data/base_adega.xlsx').read_bytes()
        cls.dados=carregar(cls.conteudo)

    def test_cenario_base(self):
        r=avaliar(self.dados)
        self.assertEqual((r['unidades'],r['custo']),(146,8184.28))
        self.assertEqual(r['contagens'].tolist(),[4,15,142,9,1,9])
        self.assertEqual(r['vendido'],1432)
        self.assertEqual(r['inicio'],pd.Timestamp('2026-05-18'))
        self.assertEqual(r['linhas'].produto_id.head(4).tolist(),[134,144,61,90])

    def test_cenarios_da_poc_original(self):
        for p,unidades,custo in [(Parametros(fator=.8),132,7293.91),(Parametros(fator=1.2),150,8480.34),(Parametros(janela=180),163,9207.13)]:
            r=avaliar(self.dados,p)
            self.assertEqual((r['unidades'],r['custo']),(unidades,custo))

    def test_limites_e_elegibilidade(self):
        df=avaliar(self.dados)['linhas']
        self.assertTrue((df.pedido>=0).all())
        self.assertTrue((df.alvo<=df.estoque_maximo).all())
        self.assertTrue((df.loc[~df.ativo|df.vendido.eq(0),'pedido']==0).all())
        self.assertTrue(df.loc[df.vendido.eq(0),'cobertura'].isna().all())

    def tabelas_cruas(self):
        return pd.read_excel(BytesIO(self.conteudo),sheet_name=None)

    def test_rejeita_chaves_duplicadas(self):
        t=self.tabelas_cruas()
        t['Estoque']=pd.concat([t['Estoque'],t['Estoque'].iloc[[0]]])
        with self.assertRaisesRegex(ValueError,'duplicada'): validar(t)

    def test_rejeita_produto_orfao(self):
        t=self.tabelas_cruas();t['Compras'].loc[0,'produto_id']=999999
        with self.assertRaisesRegex(ValueError,'sem cadastro'): validar(t)

    def test_rejeita_coluna_ausente(self):
        t=self.tabelas_cruas();t['Produtos']=t['Produtos'].drop(columns='custo_unitario')
        with self.assertRaisesRegex(ValueError,'faltam'): validar(t)

    def test_fronteiras_da_janela_e_urgencia(self):
        d={k:v.copy() for k,v in self.dados.items()}
        pid=d['Produtos'].iloc[0].produto_id
        d['Produtos']=d['Produtos'].iloc[[0]].copy(); d['Produtos']['ativo']=True
        d['Estoque']=d['Estoque'].iloc[[0]].copy()
        d['Estoque'][['estoque_atual','estoque_minimo','estoque_maximo','lead_time_dias']]=[10,5,50,10]
        d['Compras']=pd.DataFrame({'produto_id':[pid]*3,'data_compra':pd.to_datetime(['2026-05-17','2026-05-18','2026-08-15']),'quantidade':[999,45,45],'valor_total':[999,180,180]})
        r=avaliar(d);linha=r['linhas'].iloc[0]
        self.assertEqual(r['vendido'],90)
        self.assertEqual(linha.acao,'Repor urgente')
        self.assertEqual(linha.pedido,37)

    def test_arquivo_invalido_e_parametros(self):
        with self.assertRaises(ValueError): carregar(b'nao e um excel')
        with self.assertRaises(ValueError): avaliar(self.dados,Parametros(janela=0))
        with self.assertRaises(ValueError): avaliar(self.dados,Parametros(fator=float('nan')))

class InterfaceTest(unittest.TestCase):
    def test_upload_valido_e_invalido(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        app.file_uploader[0].set_value(('invalido.xlsx',b'invalido','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')).run()
        self.assertFalse(app.exception)
        self.assertIn('Não foi possível ler',app.error[0].value)
        app.file_uploader[0].set_value(('base_teste.xlsx',(ROOT/'data/base_adega.xlsx').read_bytes(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'4')
        self.assertIn('8.184,28',app.metric[3].value)

    def test_carregar_filtrar_e_simular(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'4')
        self.assertIn('8.184,28',app.metric[3].value)
        app.text_input(key='busca').set_value('77').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),1)
        self.assertEqual(app.dataframe[0].value.iloc[0]['Ação'],'Repor preventivo')
        app.number_input(key='fator').set_value(1.2).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'5')
        self.assertIn('8.480,34',app.metric[3].value)
        self.assertEqual(app.dataframe[0].value.iloc[0]['Ação'],'Repor urgente')
        app.text_input(key='busca').set_value('produto inexistente xyz').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),0)

if __name__=='__main__': unittest.main(verbosity=2)
