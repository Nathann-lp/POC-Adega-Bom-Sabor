# Adega Bom Sabor — POC em Python e Streamlit

Aplicação acadêmica de apoio à reposição de vinhos. A planilha fornecida já acompanha o projeto e é lida diretamente pelo Python. Também é possível enviar outra planilha pela barra lateral, sem editar o código. Não é necessário banco de dados, API, Node.js ou chave de IA.

## 1. Executar no Windows

Instale Python 3.11 ou 3.12, extraia o ZIP e abra a pasta `adega_streamlit` no VS Code. No terminal dessa pasta, execute:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Os comandos usam o Python do ambiente virtual diretamente, sem precisar ativá-lo ou alterar a política do PowerShell. Se `py` não existir, tente `python -m venv .venv` na primeira linha. Se ambos não existirem, instale o Python e reabra o terminal.

O navegador deverá abrir em http://localhost:8501. Deixe o terminal aberto. Para encerrar, pressione Ctrl+C no terminal. Para abrir novamente, repita somente o último comando ou dê dois cliques em `iniciar_windows.bat`, depois de instalar as dependências.

Para Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Internet é necessária para instalar as dependências. Depois, a execução local com a planilha funciona sem serviços externos. O upload é feito para o processo local do Streamlit; o aplicativo não publica dados nem emite pedidos reais.

## 2. O que cada arquivo faz

| Arquivo | Função |
|---|---|
| `app.py` | Interface, envio do Excel, filtros, cenários, explicações e download CSV. |
| `dados.py` | Leitura do Excel e validação de abas, campos, chaves, vínculos, datas e valores. |
| `modelo.py` | Fórmulas, regras de decisão, quantidades e ordenação. Não depende de Streamlit. |
| `data/base_adega.xlsx` | Cópia integral da planilha fornecida pelo usuário. |
| `requirements.txt` | Dependências da aplicação. |
| `tests/test_poc.py` | Testes do modelo, validação de dados e interação via AppTest. |
| `iniciar_windows.bat` | Inicialização após a instalação. |

Fluxo: Excel → validação → integração por produto_id → indicadores → regras → interface → decisão do gestor.

## 3. Demonstração para o trabalho

1. Inicie com a base incluída e a referência 15/08/2026.
2. Use 90 dias, demanda 1,00, segurança 7 dias, revisão 30 dias e excesso 120 dias.
3. Confira 4 urgentes, 15 preventivos, 142 suspensões e 146 unidades sugeridas por R$ 8.184,28.
4. Busque o produto 144: 16 unidades vendidas, saldo 4, cobertura 22,5 dias, prazo 31 dias e pedido 9.
5. Busque o produto 77: ação preventiva. Mude a demanda para 1,20; ele passa a urgente.
6. Na aba de cenários, confira 150 unidades e R$ 8.480,34 com fator 1,20. A coluna central sempre corresponde às condições atuais.
7. Baixe o CSV completo. Ele inclui fonte, data e parâmetros, além das evidências por produto. Os filtros da tela não limitam o CSV.

Os controles recalculam automaticamente, sem botão de confirmação. A data padrão é a última venda da planilha. Ela é apenas uma hipótese para a data do saldo. Alterá-la não reconstrói o estoque histórico. O sistema avisa se a referência difere da última venda ou se a janela precede o histórico disponível.

## 4. Alimentar com outra planilha

Use “Carregar planilha Excel” na barra lateral. O arquivo precisa ser `.xlsx`, com estes nomes exatos:

| Aba | Colunas obrigatórias |
|---|---|
| Produtos | produto_id, nome_produto, tipo, ativo, custo_unitario, preco_venda |
| Estoque | produto_id, estoque_atual, estoque_minimo, estoque_maximo, lead_time_dias |
| Compras | item_id, produto_id, data_compra, quantidade, valor_total |

`ativo` aceita Sim ou Não. Datas devem ser células de data no Excel (texto brasileiro também é convertido). Custos e preços devem ser positivos; quantidades, inteiras e positivas; saldo e limites, inteiros não negativos. Produtos e Estoque precisam ter exatamente os mesmos códigos e uma linha por produto. Cada item de compra precisa de item_id único e produto cadastrado. Colunas adicionais são ignoradas. Clientes não é obrigatória.

Dados inconsistentes bloqueiam a análise com uma mensagem; não são descartados silenciosamente. A validação não prova que o histórico comercial está completo. Compras corresponde às compras feitas pelos clientes, ou seja, vendas da adega.

O upload vale para a sessão e não substitui o arquivo incluído. Para mudar a base padrão, substitua `data/base_adega.xlsx`. Para ver uma alteração no arquivo padrão, recarregue a página. A leitura em cache usa o conteúdo do arquivo, portanto conteúdo novo gera nova leitura. Nenhum comando modifica o Excel de origem.

## 5. Modelo e limitações

- Demanda diária = vendas na janela / dias corridos × fator. Datas inicial e final incluídas.
- Cobertura = saldo / demanda; sem vendas, fica sem estimativa.
- Ponto = máximo(mínimo cadastrado, teto(demanda × (prazo + segurança))).
- Alvo = mínimo(máximo cadastrado, máximo(mínimo, teto(demanda × (prazo + segurança + revisão)))).
- Pedido = máximo(0, alvo − saldo), somente para urgente ou preventivo.

Precedência: inativo → sem vendas → urgente → suspender → preventivo → manter. Urgentes e preventivos são priorizados pela diferença cobertura menos prazo, depois margem estimada e código. As demais classes são ordenadas por capital em estoque e código.

Os parâmetros são hipóteses didáticas. Não há previsão treinada, orçamento limitado, pedidos em trânsito, reservas, lote mínimo ou simulação do consumo até a chegada. Custos usam o cadastro atual. A margem não é lucro líquido. Suspender reposição não significa retirar o produto da venda. Capital em estoque não corresponde a economia já obtida.

**Atenção ao produto 134:** a compra sugerida de 13 unidades decorre do mínimo cadastrado apesar de uma venda no período. É um exemplo para explicar por que o gestor precisa revisar parâmetros e possíveis rupturas anteriores.

## 6. Testes

No Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

No Linux/macOS use `.venv/bin/python` no lugar do executável acima. Os testes conferem os quatro cenários da POC anterior, limites, elegibilidade, fronteiras de data, chaves duplicadas, vínculos órfãos, colunas ausentes, parâmetros inválidos e interação com filtros e demanda. AppTest é o simulador oficial do Streamlit: https://docs.streamlit.io/develop/api-reference/app-testing.

O teste simulado não substitui a conferência visual no navegador do computador que será usado na apresentação.

## 7. Atualização do relatório acadêmico

A política de reposição e os resultados de referência foram preservados. Na etapa 6 e na arquitetura do relatório anterior, substitua a descrição do HTML/JavaScript por:

“A prova de conceito foi desenvolvida em Python com Streamlit. O módulo dados.py lê e valida as abas Produtos, Estoque e Compras de uma planilha Excel, utilizando pandas e openpyxl. O módulo modelo.py calcula os indicadores e aplica as regras de reposição, enquanto app.py apresenta as recomendações, permite modificar parâmetros e comparar cenários. A interface aceita uma planilha enviada pelo usuário, exporta a avaliação em CSV e apresenta a justificativa de cada produto. O sistema funciona localmente e não exige banco de dados externo.”

Esta entrega não altera o PDF do relatório anterior. A nova interface recalcula automaticamente os controles, ao contrário do botão de calcular da POC HTML.

## Fontes

Base fornecida: Base_Adega_Bom_Sabor_2026 (5)(1).xlsx. Política e cenários: POC anterior deste projeto. Orientação: Projeto Final 20261(1).pdf. Dados fictícios de finalidade acadêmica.
