"""Motor de decisão independente da interface; mesma política da POC original."""
from dataclasses import dataclass, asdict
from math import ceil, isfinite
import pandas as pd

@dataclass(frozen=True)
class Parametros:
    janela: int = 90
    fator: float = 1.0
    seguranca: int = 7
    revisao: int = 30
    excesso: int = 120

    def validar(self):
        for k, (a, b) in {'janela': (30,365), 'fator': (.25,3), 'seguranca': (0,60), 'revisao': (1,90), 'excesso': (60,365)}.items():
            v = getattr(self,k)
            if not isfinite(v) or not a <= v <= b or (k != 'fator' and int(v) != v):
                raise ValueError(f'Parâmetro inválido: {k}.')

ACOES = ['Repor urgente','Repor preventivo','Suspender reposição','Manter','Investigar sem vendas','Revisar inativo']

def avaliar(dados, param=Parametros(), referencia=None):
    param.validar()
    vendas = dados['Compras']
    fim = pd.Timestamp(referencia if referencia is not None else vendas.data_compra.max()).normalize()
    if pd.isna(fim):
        raise ValueError('Data de referência inválida.')
    inicio = fim - pd.Timedelta(days=param.janela-1)
    periodo = vendas[vendas.data_compra.between(inicio, fim)]
    resumo = periodo.groupby('produto_id').agg(vendido=('quantidade','sum'),receita=('valor_total','sum')).reset_index()
    base = dados['Produtos'].merge(dados['Estoque'],on='produto_id',validate='one_to_one').merge(resumo,on='produto_id',how='left',validate='one_to_one')
    base[['vendido','receita']] = base[['vendido','receita']].fillna(0)
    linhas = []
    for r in base.to_dict('records'):
        d = r['vendido']/param.janela*param.fator
        e, l = r['estoque_atual'], r['lead_time_dias']
        cobertura = e/d if d else None
        ponto = max(r['estoque_minimo'],ceil(d*(l+param.seguranca)))
        bruto = max(r['estoque_minimo'],ceil(d*(l+param.seguranca+param.revisao)))
        alvo = min(r['estoque_maximo'],bruto)
        margem = (r['receita']-r['vendido']*r['custo_unitario'])/r['receita'] if r['receita'] else None
        if not r['ativo']:
            prioridade, regra, motivo = 5,'R1','Produto inativo: conferir saldo e destinação antes de comprar.'
        elif not r['vendido']:
            prioridade, regra, motivo = 4,'R2','Sem vendas na janela: investigar ruptura, cadastro ou baixa procura.'
        elif cobertura <= l:
            prioridade, regra, motivo = 0,'R3','Cobertura menor ou igual ao prazo: avaliar antecipação do abastecimento.'
        elif cobertura > param.excesso or e > r['estoque_maximo']:
            prioridade, regra, motivo = 2,'R4','Cobertura acima do limite ou saldo superior ao máximo: revisar novas compras.'
        elif e < ponto:
            prioridade, regra, motivo = 1,'R5','Saldo abaixo do ponto de reposição, sem urgência pelo prazo médio.'
        else:
            prioridade, regra, motivo = 3,'R6','Saldo suficiente nas condições atuais: reavaliar na próxima revisão.'
        pedido = max(0,alvo-e) if prioridade <= 1 else 0
        alerta = 'Alvo limitado pelo máximo cadastrado. Revisar capacidade.' if bruto > r['estoque_maximo'] else ''
        if prioridade <= 1 and pedido == 0:
            alerta += ' Sem espaço para pedido: revisar limites e abastecimento.'
        capital = round(e*r['custo_unitario'],2)
        linhas.append({**r,'demanda':d,'cobertura':cobertura,'ponto':ponto,'alvo':alvo,'alvo_bruto':bruto,'margem':margem,'acao':ACOES[prioridade],'regra':regra,'motivo':motivo,'prioridade':prioridade,'pedido':pedido,'custo_pedido':round(pedido*r['custo_unitario'],2),'capital':capital,'alerta':alerta})
    linhas.sort(key=lambda x:(x['prioridade'],x['cobertura']-x['lead_time_dias'] if x['prioridade']<=1 else -x['capital'],-(x['margem'] if x['margem'] is not None else -1) if x['prioridade']<=1 else 0,x['produto_id']))
    df = pd.DataFrame(linhas)
    return {'linhas':df,'inicio':inicio,'fim':fim,'parametros':asdict(param),'itens':len(periodo),'unidades':int(df.pedido.sum()),'custo':round(df.custo_pedido.sum(),2),'contagens':df.acao.value_counts().reindex(ACOES,fill_value=0),'vendido':int(df.vendido.sum()),'receita':round(df.receita.sum(),2)}
