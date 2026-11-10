"""Leitura e validação: nenhuma alteração é gravada na planilha de origem."""
from io import BytesIO
import numpy as np
import pandas as pd

CAMPOS = {
    'Produtos': ['produto_id', 'nome_produto', 'tipo', 'ativo', 'custo_unitario', 'preco_venda'],
    'Estoque': ['produto_id', 'estoque_atual', 'estoque_minimo', 'estoque_maximo', 'lead_time_dias'],
    'Compras': ['item_id', 'produto_id', 'data_compra', 'quantidade', 'valor_total'],
}

def validar(tabelas):
    """Rejeita dados ambíguos em vez de gerar uma recomendação incompleta."""
    dados = {}
    for nome, colunas in CAMPOS.items():
        if nome not in tabelas:
            raise ValueError(f'Aba obrigatória ausente: {nome}.')
        faltam = set(colunas) - set(tabelas[nome].columns)
        if faltam:
            raise ValueError(f'{nome}: faltam as colunas {", ".join(sorted(faltam))}.')
        df = tabelas[nome][colunas].copy()
        if df.empty or df.isna().any().any():
            raise ValueError(f'{nome}: tabela vazia ou campos obrigatórios em branco.')
        texto = {'nome_produto', 'tipo', 'ativo', 'data_compra'}
        for col in set(colunas) - texto:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if not np.isfinite(df[col]).all():
                raise ValueError(f'{nome}.{col}: há números ausentes ou inválidos.')
            if col not in {'custo_unitario', 'preco_venda', 'valor_total'}:
                if ((df[col] % 1 != 0) | (df[col] < 0)).any():
                    raise ValueError(f'{nome}.{col}: use inteiros não negativos.')
                df[col] = df[col].astype('int64')
        chave = 'item_id' if nome == 'Compras' else 'produto_id'
        if df[chave].duplicated().any():
            raise ValueError(f'{nome}: chave {chave} duplicada.')
        dados[nome] = df
    p, e, c = (dados[n] for n in ['Produtos', 'Estoque', 'Compras'])
    for col in ['nome_produto', 'tipo', 'ativo']:
        p[col] = p[col].astype(str).str.strip()
        if p[col].eq('').any():
            raise ValueError(f'Produtos.{col}: texto em branco.')
    p['ativo'] = p['ativo'].str.casefold()
    if not p['ativo'].isin(['sim', 'não', 'nao']).all():
        raise ValueError('Produtos.ativo deve conter Sim ou Não.')
    p['ativo'] = p['ativo'].eq('sim')
    if (p[['custo_unitario', 'preco_venda']] <= 0).any().any():
        raise ValueError('Custos e preços devem ser positivos.')
    if (e['estoque_minimo'] > e['estoque_maximo']).any():
        raise ValueError('Há estoque mínimo superior ao máximo.')
    if set(p.produto_id) != set(e.produto_id):
        raise ValueError('Produtos e Estoque devem ter os mesmos códigos, uma linha por produto.')
    if not set(c.produto_id).issubset(set(p.produto_id)):
        raise ValueError('Compras contém produto sem cadastro.')
    if (c.quantidade <= 0).any() or (c.valor_total < 0).any():
        raise ValueError('Compras: quantidade deve ser positiva e valor não negativo.')
    if pd.api.types.is_numeric_dtype(c.data_compra):
        raise ValueError('Formate data_compra como data no Excel, não como número avulso.')
    c['data_compra'] = pd.to_datetime(c.data_compra, errors='coerce', dayfirst=True)
    if c.data_compra.isna().any():
        raise ValueError('Compras.data_compra contém datas inválidas.')
    c['data_compra'] = c.data_compra.dt.normalize()
    return dados

def carregar(conteudo: bytes):
    try:
        arquivo = pd.ExcelFile(BytesIO(conteudo), engine='openpyxl')
        tabelas = {n: pd.read_excel(arquivo, sheet_name=n) for n in CAMPOS if n in arquivo.sheet_names}
    except Exception as exc:
        raise ValueError(
            f"Falha ao ler o Excel ({type(exc).__name__}): {exc}"
        ) from exc
    return validar(tabelas)
