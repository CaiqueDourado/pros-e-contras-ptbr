# Prós e contras a partir de reviews: o que o método de 2020 errou

[Read in English](article-pros-and-cons.md)

A partir de 2020, as páginas de produto dos meus sites mostravam "Prós" e "Contras" tirados dos reviews das lojas. O notebook Samsung Expert X23, com 1.947 reviews, aparecia assim:

| Prós | Contras |
|---|---|
| Muito bom · Produto muito bom · Otimo produto · Entrega rápida | Nao recomendo · Muito lento · **A entrega foi bem rápida** · Me arrependi |

"A entrega foi bem rápida" aparece entre os contras. Este texto explica por que isso acontecia, quantas vezes acontecia, e o que mudou quando refiz o método em 2026 como biblioteca.

## O método de 2020

A apresentação que fiz na época resumia o método numa conta: **divisão de sentenças + análise de sentimentos = prós e contras**. Eram cinco passos:

1. O AWS Comprehend dá o sentimento de cada review: POSITIVE, NEGATIVE, NEUTRAL ou MIXED.
2. O Stanford POS Tagger etiqueta cada palavra.
3. O texto é cortado em cláusulas na pontuação e nas conjunções ([artigo sobre essa parte](artigo-divisao-de-clausulas.md)).
4. As cláusulas parecidas de cada produto são agrupadas por chaves fonéticas e de fingerprint.
5. As 4 cláusulas mais repetidas dos reviews POSITIVE viram prós, e as 4 dos NEGATIVE viram contras.

Parece razoável. Mas há quatro defeitos escondidos nesses passos.

## Quatro defeitos

**1. O sentimento era do review, não da cláusula.** Um review negativo diz "a entrega foi bem rápida, mas o produto é lento". As duas cláusulas herdam o NEGATIVE. Nos reviews MIXED, que são justamente os que têm prós *e* contras, nada era aproveitado.

**2. Qualquer pedaço com duas palavras contava.** O corte deixa sobrar conectivos e saudações. Os contras de um box de DVDs eram *No mais · Ainda assim · O box · Desta forma*. Produtos com poucos reviews negativos eram os mais atingidos, porque qualquer coisa repetida duas vezes chegava ao top 4.

**3. O agrupamento juntava opostos.** Bastava uma das seis chaves coincidir para duas cláusulas virarem uma só. Uma das chaves ordenava as palavras e, por um bug, pulava uma a cada duas. Com isso, "Produto de péssima qualidade" e "Produto de ótima qualidade" podiam acabar no mesmo grupo.

**4. O desempate premiava o genérico.** Entre duas cláusulas com a mesma contagem, ganhava a mais frequente no site inteiro. É o contrário do IDF: "Muito bom" vencia quase sempre.

## O que mudou

**A nota agora é por cláusula.** Ela vem de um léxico aprendido na própria base, sem anotação manual:

- uma cláusula de um review de 4 ou 5 estrelas conta como evidência positiva;
- uma cláusula de 1 ou 2 estrelas conta como negativa;
- as de 3 estrelas ficam de fora.

O peso de cada palavra é o log-odds suavizado entre os dois lados, como no "Fightin' Words" de Monroe, Colaresi e Quinn (2008). Uso as estrelas, e não o rótulo da AWS, porque elas são o julgamento do próprio cliente. Foram 9,8 milhões de cláusulas positivas e 1,9 milhão negativas, e o léxico ficou com 6.854 palavras.

A negação vira outra palavra: as três palavras depois de "não", "nunca", "nem" ou "sem" são contadas como `NOT_palavra`. O que o léxico aprendeu sozinho (palavras com peso abaixo de 0,7 ficam fora e valem zero):

| palavra | peso | | palavra | peso |
|---|---:|---|---|---:|
| funciona | +0,32 (fraco, fica fora) | | NOT_funciona | −3,35 |
| recomendo | +3,47 | | NOT_recomendo | −3,88 |
| rápida | +2,30 | | troca | −2,18 |
| atendeu | +3,25 | | NOT_atendeu | −3,58 |

**Enchimento não é opinião.** Uma cláusula só entra na lista se tiver nota de pelo menos 1,5 para um dos lados. Uma lista curta de marcadores ("fora isso", "no mais", "boa noite") nunca entra.

**O agrupamento é exato** depois de tirar acentos, plurais e stopwords. As negações são mantidas, então "não recomendo" nunca se junta com "recomendo".

**A ordem conta reviews distintos.** Repetir a frase no mesmo review não soma. O desempate é pela força da opinião, não pela frequência no site.

## Quanto melhorou

Tirei 51 produtos do treino do léxico e rotulei cada cláusula listada como *certa*, *lado errado* ou *sem opinião*. Isso vale tanto para o resultado publicado em 2020 quanto para o da biblioteca, e os dois usam as mesmas cláusulas de 2020.

| | certa | lado errado | sem opinião |
|---|---:|---:|---:|
| contras 2020 | 64,7% | 9,3% | 26,0% |
| contras 2026 | **89,7%** | 2,5% | 7,8% |
| prós 2020 | 97,1% | 0,5% | 2,5% |
| prós 2026 | **99,5%** | 0,0% | 0,5% |

O notebook do começo ficou assim:

| Prós | Contras |
|---|---|
| Muito bom · Otimo produto · Produto muito bom · Entrega rápida | Não recomendo · Achei um pouco lento · Não recomendo o produto além de ser muito lento… · O hd deu problema… |

E o box de DVDs passou de *No mais · Ainda assim · O box · Desta forma* para *Rasga a toa · …ter vindo com defeito · A capa do box veio rasgada*.

## O que ainda erra

- **Frases, não palavras.** O quarto contra do box é "De descobrir o que virá em seguida", que vem de "ansiosa de descobrir o que virá em seguida", um elogio. Ironia e dupla negação ("não tem como não se apaixonar") também passam.
- **Contras longos.** Quando um produto tem poucas reclamações repetidas, as vagas são preenchidas por cláusulas ditas uma vez só, mais longas e específicas. Com `min_mentions=2` a lista fica curta e repetida: 2 contras por produto, 89,4% certos.
- **Rótulos de uma só fonte.** Quem rotulou foi o Claude (modelo da Anthropic). Os rótulos estão no repositório para conferência, mas um segundo anotador humano daria uma medida de concordância que ainda não tenho.

## Por que um léxico e não um LLM

Um LLM escreveria prós e contras melhores para um produto. Para 222 mil produtos, com uma regra que dá para auditar palavra por palavra e que roda numa máquina comum sem custo por chamada, o léxico ainda serve. E a pergunta de 2020 continua de pé: o que os clientes *repetem* sobre o produto? Isso é contagem, não geração.

*Código, léxico e avaliação: [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr). Dados: [portuguese-product-reviews](https://github.com/CaiqueDourado/portuguese-product-reviews) ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/reviews-produtos-ptbr)). A história do site para o qual os reviews foram coletados está no [estudo de caso É bom? Vale a pena?](https://github.com/CaiqueDourado/portuguese-product-reviews/blob/main/docs/estudo-de-caso-e-bom-vale-a-pena.md).*
