# Cortar reviews em cláusulas: Google Cloud NL, Stanford e 15 linhas de regra

[Read in English](article-clause-splitting.md)

Para tirar prós e contras de reviews, primeiro é preciso cortar cada texto em pedaços que digam uma coisa só. "Bonito, mas trava muito e esquenta" tem três opiniões: *bonito*, *trava muito*, *esquenta*. Em 2020 cortei assim os reviews que coletei de lojas brasileiras (hoje 2,87 milhões). Usei três ferramentas, uma depois da outra; a terceira só veio agora, em 2026. Este texto conta o que cada uma fez e por que a última é a que fica.

## A regra é sempre a mesma

As três versões cortam com a mesma regra:

- **onde há pontuação** (um token sem letras: `,` `.` `!` `;`);
- **onde há uma conjunção**: *e, mas, ou, porém, pois…*

Algumas conjunções não cortam e ficam dentro da cláusula: *que, se, como, quando, quanto, enquanto* e *apenas*. Elas ligam uma ideia que não se sustenta sozinha: "achei **que** era maior", "**se** quiser algo bom compre outro".

O que muda de uma versão para outra é **quem diz o que é conjunção**.

## 1. Google Cloud Natural Language (até janeiro de 2020)

A primeira versão mandava cada review para o `AnalyzeSyntax` do Google Cloud NL em português. A resposta traz cada palavra com a sua classe gramatical, e o corte acontecia em `PUNCT` e `CONJ`. A qualidade era boa.

O problema era o preço: a cobrança é por texto analisado, e eram milhões de reviews, que continuavam chegando. No código ficou um comentário de **9 de janeiro de 2020: "Dei STOP. Muito caro!!!"**.

## 2. Stanford POS Tagger (2020)

O substituto foi o MaxentTagger da Stanford, rodando dentro do .NET, com um modelo de português feito por terceiros (`corenlp-model-pt`). Ele é de graça e roda local. Foi ele que cortou os 12,9 milhões de cláusulas publicados na [base de reviews](https://github.com/CaiqueDourado/reviews-produtos-ptbr).

O preço passou a ser outro: os erros do modelo. Ele erra palavras com maiúscula e linguagem coloquial:

```text
não/PNOUN Recomendo/PNOUN     gostei/NOUN     dão/ADP     aguenta/ADJ
```

Como o corte depende da etiqueta, o erro do etiquetador vira erro de corte. Exemplos tirados dos dados:

| Review | Stanford (2020) |
|---|---|
| entrega rápida antes **do** previsto | *entrega rápida antes* · *previsto* |
| é um produto **q** responde as expectativas | *é um produto* · *responde as expectativas* |
| **porém** trava muito | *porém trava muito* (não cortou) |

Antes de etiquetar, também foi preciso um pré-processamento para casos que o modelo errava:

- pôr um ponto no fim, porque "…Super indico" virava pontuação;
- proteger a barra, para "DANFE/XML" não ser cortado;
- separar pontos colados ("obrigado.de nada").

## 3. Regras, sem etiquetador (2026)

Na hora de publicar o método como biblioteca, a pergunta foi esta: se o etiquetador só serve para reconhecer pontuação e conjunções, e as conjunções coordenativas do português são uma lista curta, ele é necessário?

```python
CUT = {"e", "mas", "ou", "porém", "porem", "contudo", "todavia", "entretanto", "pois"}
KEEP = {"que", "se", "como", "quando", "quanto", "enquanto", "apenas"}
```

O [`split`](../src/pros_e_contras/clauses.py) da [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr) tokeniza o texto, corta na pontuação e nas palavras de `CUT`, e é só isso. No exemplo da apresentação de 2020, o resultado é idêntico ao do Stanford:

> Não Recomendo, vão entre as gavetas e entre a gaveta e a estrutura. A parte inferior da gaveta não dá encaixe e com isso fica impossível fechar a parte traseira do mesmo. Produto de BAIXA QUALIDADE!

→ *Não Recomendo* · *vão entre as gavetas* · *entre a gaveta* · *a estrutura* · *A parte inferior da gaveta não dá encaixe* · *com isso fica impossível fechar a parte traseira do mesmo* · *Produto de BAIXA QUALIDADE*

O exemplo também mostra o limite das duas versões: "entre a gaveta" e "a estrutura" perdem o sentido fora da frase. Um "e" que liga dois substantivos é cortado como se ligasse duas orações.

## Quanto as regras concordam com o Stanford

Comparei as regras com as cláusulas de 2020 em 15.100 reviews da amostra pública. Ficaram de fora os reviews cujo texto foi alterado na restauração de acentos.

| | Regras | spaCy `pt_core_news_sm` |
|---|---:|---:|
| Cláusulas de 2020 encontradas (recall) | 95,3% | 93,9% |
| Cláusulas que existem em 2020 (precisão) | 94,9% | 94,9% |
| Reviews cortados exatamente igual | 88,1% | 86,3% |
| Velocidade | 22 mil reviews/s | 260 reviews/s |

Pus também um etiquetador moderno na comparação, o spaCy em português, cortando com a mesma regra. Ele não chega mais perto do Stanford do que as regras, e é 85 vezes mais lento.

Lendo as diferenças, a maioria é erro do etiquetador que as regras não cometem:

- o Stanford corta em "q" e em "do";
- ele não corta em "porém" quando a palavra está sem acento ou em começo de frase.

Na outra direção, as regras deixam de cortar onde o Stanford acertou por entender a frase. Um exemplo é um "e" sem acento usado como verbo ("e lento"), que as regras cortam.

Uma escolha deliberada: as regras **não** cortam em "nem". Em review, "nem" quase sempre é negação ("nem liga", "não atende nem o básico"), e separar a negação do verbo inverte a opinião.

## O que fica

| | Google Cloud NL | Stanford + modelo PT | Regras |
|---|---|---|---|
| Custo | pago por texto | grátis, local | grátis, local |
| Dependências | API e chave | Java via IKVM e modelo de terceiros | nenhuma |
| Velocidade | uma chamada de rede por review | etiqueta palavra por palavra | cerca de 22 mil reviews por segundo (2,87 milhões em uns 2 minutos) |
| Erros típicos | poucos | maiúsculas, coloquial | "e" ligando substantivos |

Para esta tarefa, cortar opiniões em reviews, o etiquetador não pagava o que custava. A biblioteca usa as regras por padrão. Ela também aceita um etiquetador (`spacy_tagger("pt_core_news_sm")`) para quem quiser os cortes guiados pela gramática, e o [`split_tagged`](../src/pros_e_contras/clauses.py) reproduz a regra de 2020 sobre texto já etiquetado.

Cortar bem é só metade do caminho. A outra metade, decidir se cada cláusula é pró ou contra, está no [artigo sobre prós e contras](artigo-pros-e-contras.md).

*Código e avaliação: [evaluation/splitter_agreement.py](../evaluation/splitter_agreement.py). Dados: [reviews-produtos-ptbr](https://github.com/CaiqueDourado/reviews-produtos-ptbr) ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/reviews-produtos-ptbr)).*
