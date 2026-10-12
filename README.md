# FLOPPY

**Um jogo de blocos 3D roguelike jogado dentro de uma máquina de arcade, onde programas
gravados em disquetes — os *hacks* — reescrevem as regras da partida.**

Projeto da disciplina de Algoritmos e Estruturas de Dados I — Centro de Ciências
Computacionais, Universidade Federal do Rio Grande (FURG).

---

## O jogo

O jogador está diante de uma máquina de arcade que roda um jogo de blocos tridimensional.
Cada linha completada dispara um ataque contra o oponente — um adversário
controlado por inteligência artificial que joga na grade ao lado. O ataque não é
enviado na hora: ele abre uma **barra de ataque** que segura o dano por alguns
segundos enquanto acumula multiplicadores, de modo que encadear limpezas rápidas
vale muito mais do que limpar linhas isoladas.

Ao longo da partida, leitores de disquete acoplados ao gabinete permitem instalar
**hacks**: programas que ficam ativos permanentemente e distorcem o jogo a favor
do jogador — alguns mexem na mecânica (melhor controle de peça, rotações extras,
peças reservadas), outros multiplicam ou somam bônus direto na barra de ataque.
Cada partida combina hacks diferentes, e é dessa combinação que nasce a variação
roguelike.

Todo o desenho na tela é feito por um **pipeline gráfico escrito do zero**. A
biblioteca Pyxel é usada exclusivamente como superfície de vídeo: o jogo escreve
diretamente no *framebuffer* de índices de paleta que ela expõe. Projeção,
recorte, rasterização, teste de profundidade, amostragem de textura e iluminação
são calculados na CPU com NumPy — não há OpenGL, nem `pyxel.tri`, nem
`pyxel.blt` desenhando a cena.

## Conceitos de STEAM

O projeto foi construído de modo que as cinco áreas de STEAM apareçam como parte
funcional do jogo, e não como enfeite.

### Science — Ciência

A iluminação reproduz o comportamento físico da luz sobre superfícies. A
componente difusa segue a **lei do cosseno de Lambert** (o brilho de um ponto é
proporcional ao cosseno do ângulo entre a normal da superfície e a direção da
luz), e a intensidade cai com o **inverso do quadrado da distância** até a fonte.
A componente especular modela a reflexão em torno do vetor refletido, com
expoente controlando o quão concentrado é o brilho. Como a paleta tem apenas 16
cores, o resultado contínuo desse cálculo é *quantizado* em faixas discretas —
uma cor para superfície em luz normal, outra para região iluminada, branco para
os pontos de maior intensidade e preto para ausência de luz.

### Technology — Tecnologia

O renderizador é uma reimplementação em software daquilo que uma GPU faria:
transformação de vértices, recorte contra o plano próximo, divisão perspectiva,
mapeamento para coordenadas de tela, rasterização por caixa envolvente,
*z-buffer* e estágio de fragmento. Tudo é escrito de forma **vetorizada com
NumPy**: os triângulos do quadro inteiro são projetados de uma vez, agrupados
pelo tamanho da caixa envolvente e rasterizados grupo a grupo, e todos os
fragmentos são resolvidos contra o *z-buffer* numa única operação
(`np.maximum.at`). Um laço em Python por triângulo seria ordens de grandeza mais
lento. A persistência de hacks, recordes e
configuração de teclas é feita em **arquivos de texto**, sem banco de dados. O
código é versionado em Git.

### Engineering — Engenharia

A arquitetura é dividida em camadas independentes (`renderer/`, `game/`, `ai/`,
`platform/`, `shaders/`), de modo que a lógica de jogo não sabe como os pixels
chegam à tela e o renderizador não sabe o que é uma peça. A IA
adversária resolve um problema de engenharia clássico: **orçamento de tempo por
quadro**. Em vez de buscar a melhor jogada de uma vez e travar a imagem, ela faz
uma busca em largura sobre as entradas (cada posição que a peça alcança com
movimentos, giros e *kicks*) incremental, executando um número limitado de
estados por quadro e retomando de onde parou no quadro seguinte.

### Arts — Artes

Toda a identidade visual é autoral: as texturas são pintadas à mão, a paleta de
16 cores é escolhida para sustentar a iluminação em faixas, e os modelos 3D — o
gabinete de arcade, a sala em que ele está, os leitores de disquete e os próprios
disquetes, cada um com arte de rótulo própria — são modelados para o projeto. O
resultado busca a estética de arcade dos anos 80 sob restrição deliberada de
cores e resolução.

### Mathematics — Matemática

O jogo é, em boa medida, álgebra linear aplicada. Matrizes de modelo, visão e
projeção compõem a transformação de mundo para tela; a matriz de visão é montada
a partir de **produtos vetoriais** e **normalização** para obter uma base
ortonormal da câmera. A rasterização usa **coordenadas baricêntricas** tanto para
decidir se um pixel está dentro do triângulo quanto para interpolar profundidade,
normais e coordenadas de textura — com correção perspectiva, que exige interpolar
em `1/w`. As rotações das peças seguem o sistema SRS, com tabelas de deslocamento
por estado de rotação. E a IA avalia cada jogada com uma **heurística ponderada**
(altura agregada, buracos, irregularidade, linhas limpas), no espírito do
algoritmo de Dellacherie.

## Como executar

Requisitos: Python 3.12+, com `pyxel`, `numpy` e `pillow`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyxel numpy pillow

./run.sh
```

O progresso (árvore de magia, pontos, inimigo atual, disquetes) fica em
`floppy.save`, um arquivo de texto; outro caminho pode ser passado como primeiro
argumento.

### Controles

Na sala:

| Tecla | Ação |
|-------|------|
| setas | andar / virar |
| `Enter` | sentar no arcade / levantar |
| `Tab` | menu da magia (árvore de habilidades) |

Sentado no arcade:

| Tecla | Ação |
|-------|------|
| `J` / `L` | mover peça para a esquerda / direita |
| `D` / `C` | girar no sentido horário / anti-horário |
| `A` | girar 180° |
| `B` | queda suave |
| `I` | queda suave instantânea |
| `S` | queda instantânea |
| `K` / `U` | reservar peça (segunda reserva com a magia) |

### Como a partida anda

O arcade começa como um jogo de blocos comum, com peças planas. A primeira *quadra*
(quatro linhas com a peça I) desperta a magia: as peças saltam da tela em 3D e o
primeiro inimigo aparece ao lado do gabinete. Derrotar o inimigo *n* dá *n* pontos
de magia e a escolha de um entre três disquetes (*hacks*), que só funcionam com
leitores comprados na árvore. Perder apaga os disquetes e volta ao inimigo 1; a
árvore fica.

## Estrutura do projeto

```
src/floppy/
├── __main__.py   janela, câmera, entrada, menus e HUD
├── scene.py      paleta, iluminação e geometria: sala, gabinete, tabuleiros
├── renderer/     pipeline gráfico em lote (batch.py) e matrizes (math3d.py)
├── game/
│   ├── rules.py  regras: bitboard, peças, SRS, spins, ataque, barra, lixo
│   ├── ai.py     oponente: busca por entradas, perfis e heurística
│   └── play.py   controle da peça, luta, progressão, árvore e salvamento
└── assets/       texturas
tests/            testes das regras
```

## Licença

Projeto acadêmico.
