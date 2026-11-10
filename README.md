# Adega Bom Sabor

Sistema de apoio à decisão para reposição de vinhos, desenvolvido em Python e Streamlit. A partir de uma planilha Excel com cadastro, saldo e vendas, a aplicação indica **quais produtos repor, quantas unidades comprar e quanto a compra custaria**. O gestor pode conferir a justificativa por vinho e simular mudanças na demanda antes de decidir.

A prova de conceito (POC) acompanha uma base acadêmica fictícia com 180 produtos e roda localmente.

## Executar o projeto

Use Python 3.12. Clone o repositório e entre na pasta do projeto.

```bash
git clone https://github.com/Nathann-lp/POC-Adega-Bom-Sabor.git
cd POC-Adega-Bom-Sabor
```

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**Linux ou macOS**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Abra [localhost:8501](http://localhost:8501) no navegador. A aplicação carrega automaticamente a [planilha de exemplo](data/base_adega.xlsx). Para encerrar, pressione `Ctrl+C` no terminal. No Windows, após a instalação, também é possível iniciar pelo arquivo [iniciar_windows.bat](iniciar_windows.bat).

## Experimente com um vinho

1. Na aba **Recomendações**, mantenha os parâmetros iniciais e busque o código **144**. O Tinto Merlot Douro 2023 vendeu 16 unidades em 90 dias. Nesse ritmo, as 4 unidades em estoque duram **22,5 dias**.
2. Compare a cobertura com o prazo de entrega de **31 dias**. Como o saldo pode acabar antes da entrega, o sistema indica **Repor urgente**. O estoque-alvo é de 13 unidades. Descontando as 4 disponíveis, o pedido sugerido é de **9 unidades**.
3. Abra **Comparar cenários** para ver como o pedido da adega inteira muda com a demanda. Em **Recomendações**, o botão **Baixar avaliação completa (CSV)** exporta todos os produtos, inclusive quando a tabela está filtrada.

### Resultados com a base incluída

Referência de **15/08/2026**, histórico de 90 dias, segurança de 7 dias, revisão de compras a cada 30 dias e limite de excesso de 120 dias de cobertura.

| Demanda simulada | Produtos urgentes | Produtos preventivos | Unidades sugeridas | Custo estimado |
| --- | ---: | ---: | ---: | ---: |
| 20% menor | 2 | 15 | 132 | R$ 7.293,91 |
| Original | 4 | 15 | 146 | R$ 8.184,28 |
| 20% maior | 5 | 15 | 150 | R$ 8.480,34 |

## Como o sistema decide

A demanda diária é a quantidade vendida na janela dividida pelo número de dias corridos, multiplicada pelo fator de simulação. A **cobertura** é o saldo atual dividido por essa demanda. O modelo examina as regras abaixo em ordem e aplica a primeira condição atendida.

| Regra | Condição | Ação exibida |
| --- | --- | --- |
| R1 | Produto inativo | Revisar inativo |
| R2 | Nenhuma unidade vendida na janela | Investigar sem vendas |
| R3 | Cobertura menor ou igual ao prazo de entrega | Repor urgente |
| R4 | Cobertura acima do limite de excesso ou saldo acima do máximo cadastrado | Suspender reposição |
| R5 | Saldo abaixo do ponto de reposição | Repor preventivo |
| R6 | Demais casos | Manter |

O **ponto de reposição** cobre a demanda durante o prazo de entrega mais os dias de segurança, respeitando o mínimo cadastrado. O **estoque-alvo** acrescenta os dias até a próxima revisão e respeita os limites mínimo e máximo. Ambos os cálculos arredondam a demanda para cima. Nas ações urgente e preventiva, a quantidade sugerida é `máximo(0, estoque-alvo − saldo)`. O custo usa o custo unitário atual de cada produto.

**Limites de interpretação.** A planilha informa o saldo sem registrar sua data. Por isso, a aplicação assume a data da última venda como referência inicial. Alterar essa data desloca a janela de vendas e mantém o saldo informado. As simulações usam regras e médias históricas. Cabe ao gestor considerar pedidos em trânsito, restrições de orçamento e possíveis períodos de falta do produto antes de comprar.

## Usar outra planilha

Na barra lateral, selecione **Carregar planilha Excel** e envie um arquivo `.xlsx` com as três abas abaixo. A aba **Compras** representa as compras dos clientes, ou seja, as vendas da adega.

| Aba | Colunas obrigatórias |
| --- | --- |
| Produtos | `produto_id`, `nome_produto`, `tipo`, `ativo`, `custo_unitario`, `preco_venda` |
| Estoque | `produto_id`, `estoque_atual`, `estoque_minimo`, `estoque_maximo`, `lead_time_dias` |
| Compras | `item_id`, `produto_id`, `data_compra`, `quantidade`, `valor_total` |

Use os mesmos códigos em **Produtos** e **Estoque**, com uma linha por produto em cada aba. Em **Compras**, cada item precisa de um `item_id` único, de um produto cadastrado e de uma quantidade inteira positiva. Preencha `ativo` com `Sim` ou `Não` e formate `data_compra` como data no Excel. O aplicativo informa inconsistências antes de gerar recomendações. O envio vale para a sessão. Para trocar a base padrão, substitua `data/base_adega.xlsx`.

## Organização do código

| Arquivo | Responsabilidade |
| --- | --- |
| [dados.py](dados.py) | Lê o Excel com pandas e openpyxl e valida campos, chaves e vínculos entre abas. |
| [modelo.py](modelo.py) | Calcula os indicadores, classifica cada produto e ordena as recomendações. |
| [app.py](app.py) | Apresenta a análise em Streamlit, recebe a planilha, compara cenários e exporta o CSV. |
| [tests/test_poc.py](tests/test_poc.py) | Verifica resultados de referência, limites das regras, validação dos dados e interações da interface. |

Para executar os testes após instalar as dependências, use o comando do seu sistema na raiz do repositório.

**Windows**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Linux ou macOS**

```bash
.venv/bin/python -m unittest discover -s tests -v
```
