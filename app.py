from pathlib import Path
from dataclasses import replace
from hashlib import sha256
import pandas as pd
import streamlit as st
from dados import carregar
from modelo import avaliar, Parametros, ACOES

st.set_page_config(page_title='Adega Bom Sabor | SAD',page_icon='🍷',layout='wide')

def moeda(v):
    return 'R$ '+f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

@st.cache_data(show_spinner=False)
def ler_excel(conteudo):
    return carregar(conteudo)

st.title('Adega Bom Sabor')
st.caption('Sistema de Apoio à Decisão • Planejamento da reposição • POC acadêmica')
st.sidebar.header('Base de dados')
enviado = st.sidebar.file_uploader('Carregar planilha Excel',type=['xlsx'],help='Abas obrigatórias: Produtos, Estoque e Compras.')
padrao = Path(__file__).parent/'data'/'base_adega.xlsx'
try:
    conteudo = enviado.getvalue() if enviado is not None else padrao.read_bytes()
    nome = enviado.name if enviado is not None else 'base_adega.xlsx (fornecida no projeto)'
    dados = ler_excel(conteudo)
except (ValueError,OSError) as exc:
    st.error(str(exc)); st.info('Use a planilha original ou confira as abas e colunas no README.'); st.stop()

digest = sha256(conteudo).hexdigest()
vendas = dados['Compras']
ultima = vendas.data_compra.max().date()
if st.session_state.get('base_digest') != digest:
    st.session_state['referencia'] = ultima
    st.session_state['base_digest'] = digest

st.sidebar.caption(f'Fonte: {nome}')
st.sidebar.header('Condições da análise')
ref = st.sidebar.date_input('Data de referência do estoque',key='referencia',help='O Excel não identifica a data do saldo. A última venda é uma hipótese inicial; altere somente para a data correspondente ao saldo da planilha.')
janela = st.sidebar.number_input('Histórico (dias)',30,365,90,1,key='janela')
fator = st.sidebar.number_input('Multiplicador da demanda',.25,3.0,1.0,.05,key='fator')
seg = st.sidebar.number_input('Segurança (dias)',0,60,7,1,key='seguranca')
rev = st.sidebar.number_input('Revisão de compras (dias)',1,90,30,1,key='revisao')
exc = st.sidebar.number_input('Excesso de cobertura (dias)',60,365,120,1,key='excesso')
st.sidebar.caption('Recalcula automaticamente ao alterar as condições. 1,20 simula demanda 20% maior.')
p = Parametros(janela,fator,seg,rev,exc)
r = avaliar(dados,p,ref)
df = r['linhas']
st.info(f'Referência assumida do saldo: {ref:%d/%m/%Y}. Confirme essa data antes de usar as recomendações. Alterar a data não reconstrói estoques passados.')
if ref != ultima:
    st.warning(f'A referência difere da última venda ({ultima:%d/%m/%Y}). Verifique a cobertura temporal da base e a data do saldo.')
if r['inicio'] < vendas.data_compra.min():
    st.warning('A janela começa antes da primeira venda da base. Dias sem registros entram no denominador; verifique se o histórico é completo.')
if not r['itens']:
    st.warning('Não há vendas na janela selecionada. A POC não recomenda compras com base em demanda zero.')
st.caption(f'Janela inclusiva: {r["inicio"]:%d/%m/%Y} a {r["fim"]:%d/%m/%Y} • {r["itens"]:,} itens de transação • {r["vendido"]:,} unidades vendidas')
for col,(label,value) in zip(st.columns(4),[('Reposição urgente',int(r['contagens']['Repor urgente'])),('Suspender reposição',int(r['contagens']['Suspender reposição'])),('Unidades sugeridas',r['unidades']),('Custo estimado',moeda(r['custo']))]):
    col.metric(label,value)

recomendacoes,cenarios,qualidade,metodo = st.tabs(['Recomendações','Comparar cenários','Dados e validação','Como funciona'])
with recomendacoes:
    st.subheader('Prioridades e evidências')
    a,b,c = st.columns([2,1,1])
    busca = a.text_input('Buscar nome ou código',key='busca')
    acao = b.selectbox('Ação',['Todas']+ACOES)
    tipo = c.selectbox('Tipo',['Todos']+sorted(df.tipo.unique().tolist()))
    filtro = df.copy()
    if busca:
        filtro = filtro[filtro.produto_id.eq(int(busca.strip()))] if busca.strip().isdigit() else filtro[filtro.nome_produto.str.contains(busca,case=False,regex=False)]
    if acao != 'Todas': filtro = filtro[filtro.acao.eq(acao)]
    if tipo != 'Todos': filtro = filtro[filtro.tipo.eq(tipo)]
    nomes={'produto_id':'Código','nome_produto':'Produto','acao':'Ação','vendido':'Vendas (un.)','estoque_atual':'Saldo (un.)','cobertura':'Cobertura (dias)','lead_time_dias':'Prazo (dias)','ponto':'Ponto (un.)','alvo':'Alvo (un.)','pedido':'Pedido (un.)','custo_pedido':'Custo (R$)'}
    st.caption(f'{len(filtro)} de {len(df)} produtos. Indicadores, cenários e exportação abrangem todos os produtos.')
    st.dataframe(filtro[list(nomes)].rename(columns=nomes).round(2),hide_index=True,width='stretch')
    if not filtro.empty:
        cod = st.selectbox('Produto para explicar a recomendação',filtro.produto_id.tolist(),format_func=lambda x:f'#{x} — {df.loc[df.produto_id.eq(x),"nome_produto"].iloc[0]}')
        linha = df.loc[df.produto_id.eq(cod)].iloc[0]
        st.markdown(f'**{linha.acao} · {linha.regra}**')
        st.write(linha.motivo)
        cobertura = 'sem estimativa' if pd.isna(linha.cobertura) else f'{linha.cobertura:.2f} dias'
        st.write(f'Demanda estimada: {linha.demanda:.4f} un./dia. Cobertura: {cobertura}. Prazo: {linha.lead_time_dias} dias. Ponto: {linha.ponto} un. Alvo: {linha.alvo} un.')
        st.write(f'Pedido sugerido: {linha.pedido} un. Custo: {moeda(linha.custo_pedido)}. Capital em estoque: {moeda(linha.capital)}.')
        if linha.alerta: st.warning(linha.alerta)
    export = df.copy()
    export['referencia'] = ref.isoformat()
    export['fonte'] = nome
    for k,v in r['parametros'].items(): export['param_'+k] = v
    # Protege textos enviados pelo usuário contra fórmulas ao abrir o CSV em planilhas.
    for col in export.select_dtypes(include=['object','string']):
        export[col] = export[col].map(lambda x: "'"+x if isinstance(x,str) and x.lstrip().startswith(('=','+','-','@')) else x)
    st.download_button('Baixar avaliação completa (CSV)',export.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'avaliacao_adega.csv','text/csv')
with cenarios:
    st.subheader('Sensibilidade à demanda')
    comp = []
    for label,mult in [('Demanda −20%',max(.25,fator*.8)),('Cenário atual',fator),('Demanda +20%',min(3.,fator*1.2))]:
        s = avaliar(dados,replace(p,fator=mult),ref)
        comp.append({'Cenário':label,'Fator efetivo':mult,'Urgentes':int(s['contagens']['Repor urgente']),'Preventivos':int(s['contagens']['Repor preventivo']),'Suspender':int(s['contagens']['Suspender reposição']),'Pedido (un.)':s['unidades'],'Custo (R$)':s['custo']})
    st.dataframe(pd.DataFrame(comp).round(2),hide_index=True,width='stretch')
    st.caption('Todos os cenários usam a mesma janela e os mesmos limites. O fator efetivo respeita o intervalo 0,25 a 3,00. São simulações, não previsões validadas.')
    st.subheader('Produtos por ação no cenário atual')
    st.bar_chart(r['contagens'])
with qualidade:
    st.subheader('Dados carregados diretamente do Excel')
    st.success('Validações obrigatórias aprovadas: esquema, campos preenchidos, números, datas, chaves, vínculos e limites de estoque.')
    st.write(f'{len(dados["Produtos"])} produtos • {len(dados["Estoque"])} saldos • {len(vendas)} itens de compra.')
    st.write(f'Histórico disponível: {vendas.data_compra.min():%d/%m/%Y} a {vendas.data_compra.max():%d/%m/%Y}.')
    st.caption('Validações estruturais não comprovam qualidade comercial ou completude histórica. Clientes não é necessária à decisão por produto. A planilha original não é alterada.')
    for n,t in dados.items():
        with st.expander(f'{n} — dados selecionados e normalizados'): st.dataframe(t,hide_index=True,width='stretch')
with metodo:
    st.markdown('''### Mecanismo de apoio
1. **R1 — Inativo:** revisar cadastro e saldo; não comprar automaticamente.
2. **R2 — Sem vendas:** investigar, pois ausência de vendas pode decorrer de ruptura.
3. **R3 — Urgente:** cobertura menor ou igual ao prazo do fornecedor.
4. **R4 — Suspender:** cobertura acima do limite ou saldo acima do máximo.
5. **R5 — Preventivo:** saldo abaixo do ponto de reposição.
6. **R6 — Manter:** nenhuma condição anterior.

As regras são aplicadas nessa ordem. Demanda = vendas / dias × fator. Cobertura = saldo / demanda.
Ponto = máximo(mínimo, teto(demanda × (prazo + segurança))).
Alvo = mínimo(máximo cadastrado, máximo(mínimo, teto(demanda × (prazo + segurança + revisão)))).
Pedido = máximo(0, alvo − saldo), somente para ações de reposição.

**Ordenação:** urgentes, preventivos, suspensão, manutenção, sem vendas e inativos.
Nas reposições, menor (cobertura − prazo), maior margem estimada e código.
Nas demais ações, maior capital em estoque e código.

**Arquitetura:** Excel → leitura e validação (`dados.py`) → cálculos e regras (`modelo.py`) → interação (`app.py`) → gestor.

**Limitações:** referência do saldo assumida; custo atual; demanda média; sem pedidos em trânsito,
reservas, lotes mínimos ou orçamento. O alvo representa o momento da análise e não simula a chegada.
Margem é estimada com custo atual e receita histórica. Capital em estoque não é economia comprovada.
Os parâmetros são hipóteses didáticas. Não há IA treinada nem envio automático de compras.
''')
