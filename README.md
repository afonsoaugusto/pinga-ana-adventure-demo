# pinga-ana-adventure-demo

Demo **pygame-ce** empacotada com **pygbag** (async + `await asyncio.sleep(0)` no loop).

## Se o site abrir em branco ou só mostrar este README

No GitHub: **Settings → Pages → Source: GitHub Actions**. Enquanto a origem for uma **branch** com `README.md` na raiz, o GitHub usa **Jekyll** — não o `index.html` do pygbag.

## Queres `http://afonsorodrigues.com/pinga-ana-adventure-demo/` (apex + pasta)

O GitHub **não** publica o Pages **deste** repositório de projeto nesse URL quando o apex `afonsorodrigues.com` já é servido pelo repositório **`<utilizador>.github.io`** (site pessoal na raiz). O redirect pode existir, mas o conteúdo do jogo nunca chega a essa pasta — daí o 404.

**Solução suportada por este repo:** copiar o `build/web` para **dentro** do repo `<utilizador>.github.io`, na pasta **`static/pinga-ana-adventure-demo/`** (site **Hugo**). O Hugo só publica o que vai para `public/`; tudo em `static/` é copiado tal como está para `public/pinga-ana-adventure-demo/`. Se o bundle ficar na **raiz** do repo, o workflow do Hugo **não** o inclui no deploy — o URL cai no layout do blog (404 ou página vazia com tema). O pygbag usa caminhos relativos ao `index.html`, por isso a subpasta no URL mantém-se a mesma.

### 1. Repositório `afonsoaugusto.github.io`

- Deve existir o repo **`afonsoaugusto/afonsoaugusto.github.io`** (ou o da tua org equivalente).
- **Custom domain** e DNS do `afonsorodrigues.com` ficam nas **Settings → Pages** desse repo (não no do jogo).

### 2. Neste repo (`pinga-ana-adventure-demo`)

**Settings → Secrets and variables → Actions** (separadores **Secrets** e **Variables** ao **nível do repositório** — não coloques só em *Environments → github-pages*: o workflow usa `vars.USER_SITE_REPO`, que **não** inclui variáveis desse *Environment*.)

| Tipo | Nome | Valor |
|------|------|--------|
| **Variable** | `USER_SITE_REPO` | `afonsoaugusto/afonsoaugusto.github.io` (owner/repo do site no apex) |
| **Variable** (opcional) | `USER_SITE_BRANCH` | Branch onde está o site, por defeito o workflow usa `main` |
| **Secret** | `USER_PAGES_TOKEN` | Personal Access Token com permissão para dar **push** nesse repo `.github.io` (âmbito `repo` ou pelo menos conteúdo nesse repositório) |

Com `USER_SITE_REPO` **definida**, o workflow **deixa de** usar “GitHub Pages deste repo” e faz **clone + `git add -f`** da pasta **`static/pinga-ana-adventure-demo/`** no repositório `.github.io`. O `-f` evita que o **`.gitignore` do site** remova ficheiros do pygbag (`.apk`, `.wasm`, `.js`, etc.); sem isso, às vezes só o `.nojekyll` era comitado.

### Depois de alterares variables ou o PAT

**Guardar variables não dispara o workflow.** Tens de:

1. **Actions** → workflow **Deploy pygbag to GitHub Pages** → **Run workflow** → **Run workflow**, **ou**
2. Fazer um **push** qualquer à branch `main` (por exemplo um commit vazio: `git commit --allow-empty -m "chore: trigger pages" && git push`).

No log do job **build**, o passo **Resumo do modo de deploy** deve mostrar se `USER_SITE_REPO` foi lido (se continuar “vazio”, a variable está noutro sítio ou com nome errado). Falta de **USER_PAGES_TOKEN** falha ainda no job **build**, antes do push para o `.github.io`.

### 3. Ajustar Pages **deste** repo do jogo

Para não haver redirect estranho nem conflito:

- **Settings → Pages → Custom domain**: remove / deixa vazio neste repositório.
- Opcional: desliga Pages neste repo se já não precisares do URL `github.io/pinga-ana-adventure-demo/`.

### 4. Branch do site

O workflow publica na branch **`main`** por omissão. Se o teu `.github.io` usar outra (ex.: `master`), cria a variable **`USER_SITE_BRANCH`** com esse nome (e confirma que a expressão no workflow é suportada; se falhar, edita `.github/workflows/pygbag-pages.yml` e fixa `publish_branch`).

Depois de um push com sucesso, o jogo deve abrir em **`http://afonsorodrigues.com/pinga-ana-adventure-demo/`** (e HTTPS quando activares **Enforce HTTPS** no repo `.github.io`).

### 5. A URL mostra o README (Jekyll) ou o layout do blog (Hugo) em vez do jogo

- **Jekyll (GitHub Pages “branch”):** se existir **`…/README.md`** na pasta publicada e **não** existir **`index.html`**, o Jekyll pode transformar o README em página.

- **Hugo (site em `afonsoaugusto.github.io` com Actions):** o deploy publica só o conteúdo de **`public/`** após `hugo`. Ficheiros na **raiz** do repo (ex.: `pinga-ana-adventure-demo/` fora de `static/`) **não** entram no site — o caminho `/pinga-ana-adventure-demo/` fica sem o bundle e vês página do tema (404, lista vazia, etc.). O bundle tem de estar em **`static/pinga-ana-adventure-demo/`** para o Hugo copiar para **`public/pinga-ana-adventure-demo/`**.

O workflow **remove `README.md`** da pasta de deploy em cada job e exige **`index.html`**. Confirma no GitHub que existe [`static/pinga-ana-adventure-demo/index.html`](https://github.com/afonsoaugusto/afonsoaugusto.github.io/tree/main/static/pinga-ana-adventure-demo) (e `.apk`/`.tar.gz`, etc.). Se só aparecer `.nojekyll`, o deploy do Actions ainda não correu com sucesso ou falhou antes do push.

Opcional: **`.nojekyll` na raiz** do repo `.github.io` desactiva o Jekyll para **todo** o site quando a origem do Pages for uma branch (útil em sites estáticos sem Hugo Actions).

## Sem `USER_SITE_REPO` (só GitHub Pages deste repo)

Com a variable **vazia / não definida**, o fluxo antigo mantém-se: artefacto → **Deploy pygbag to GitHub Pages** → URL `https://<user>.github.io/pinga-ana-adventure-demo/`.

## Build local

```bash
pip install -r requirements.txt
python -m pygbag --build --template ci/default.tmpl --icon ci/favicon.png .
```

Saída em `build/web/`.

**Nota:** em `pygbag.ini`, não uses entradas em `ignoreDirs` com **espaços** no caminho (ex.: `/assets/Aseprite file`) — o pygbag aborta antes de gerar `index.html`. O CI usa template e ícone em `ci/` para não depender só do CDN.
