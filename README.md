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
NumPy**, operando sobre matrizes de pixels inteiras em vez de laços em Python,
que seria ordens de grandeza mais lento. A persistência de hacks, recordes e
configuração de teclas é feita em **arquivos de texto**, sem banco de dados. O
código é versionado em Git.

### Engineering — Engenharia

A arquitetura é dividida em camadas independentes (`renderer/`, `game/`, `ai/`,
`platform/`, `shaders/`), de modo que a lógica de jogo não sabe como os pixels
chegam à tela e o renderizador não sabe o que é uma peça. A IA
adversária resolve um problema de engenharia clássico: **orçamento de tempo por
quadro**. Em vez de buscar a melhor jogada de uma vez e travar a imagem, ela faz
uma busca em feixe (*beam search*) incremental, executando um número limitado de
simulações por quadro e retomando de onde parou no quadro seguinte.

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

### Controles

| Tecla | Ação |
|-------|------|
| `J` / `L` | mover peça para a esquerda / direita |
| `D` / `C` | girar no sentido horário / anti-horário |
| `A` | girar 180° |
| `B` | queda suave |
| `S` | queda instantânea |
| `K` | reservar peça |

## Estrutura do projeto

```
src/floppy/
├── renderer/     pipeline gráfico: câmera, matrizes, recorte, rasterizador,
│                 z-buffer, textura, luz, geometria 2D
├── shaders/      estágios de vértice e fragmento executados na CPU
├── game/         regras: peças, grade, rotações, ataque, hacks, animações
├── ai/           oponente: simulação em bitboard, heurística, busca em feixe
├── platform/     janela, entrada de teclado e temporização
└── assets/       texturas e modelos
tests/            testes automatizados por módulo
```

## Licença

Projeto acadêmico.
