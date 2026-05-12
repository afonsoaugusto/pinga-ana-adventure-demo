# pinga-ana-adventure-demo

Demo **pygame-ce** empacotada com **pygbag** (async + `await asyncio.sleep(0)` no loop).

## Se o site abrir em branco ou só mostrar este README

No GitHub: **Settings → Pages → Source: GitHub Actions**. Enquanto a origem for uma **branch** com `README.md` na raiz, o GitHub usa **Jekyll** — não o `index.html` do pygbag.

## Queres `http://afonsorodrigues.com/pinga-ana-adventure-demo/` (apex + pasta)

O GitHub **não** publica o Pages **deste** repositório de projeto nesse URL quando o apex `afonsorodrigues.com` já é servido pelo repositório **`<utilizador>.github.io`** (site pessoal na raiz). O redirect pode existir, mas o conteúdo do jogo nunca chega a essa pasta — daí o 404.

**Solução suportada por este repo:** copiar o `build/web` para **dentro** do repo `<utilizador>.github.io`, na pasta **`pinga-ana-adventure-demo/`**, onde o teu domínio já está configurado. O pygbag usa caminhos relativos ao `index.html`, por isso isto funciona nessa subpasta.

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

Com `USER_SITE_REPO` **definida**, o workflow **deixa de** usar “GitHub Pages deste repo” e passa a fazer push da pasta `pinga-ana-adventure-demo/` no outro repositório ([peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)).

### Depois de alterares variables ou o PAT

**Guardar variables não dispara o workflow.** Tens de:

1. **Actions** → workflow **Deploy pygbag to GitHub Pages** → **Run workflow** → **Run workflow**, **ou**
2. Fazer um **push** qualquer à branch `main` (por exemplo um commit vazio: `git commit --allow-empty -m "chore: trigger pages" && git push`).

No log do job **build**, o passo **Resumo do modo de deploy** deve mostrar se `USER_SITE_REPO` foi lido (se continuar “vazio”, a variable está noutro sítio ou com nome errado). No job **deploy-user-site-subpath**, se faltar o PAT, o workflow falha logo com mensagem explícita.

### 3. Ajustar Pages **deste** repo do jogo

Para não haver redirect estranho nem conflito:

- **Settings → Pages → Custom domain**: remove / deixa vazio neste repositório.
- Opcional: desliga Pages neste repo se já não precisares do URL `github.io/pinga-ana-adventure-demo/`.

### 4. Branch do site

O workflow publica na branch **`main`** por omissão. Se o teu `.github.io` usar outra (ex.: `master`), cria a variable **`USER_SITE_BRANCH`** com esse nome (e confirma que a expressão no workflow é suportada; se falhar, edita `.github/workflows/pygbag-pages.yml` e fixa `publish_branch`).

Depois de um push com sucesso, o jogo deve abrir em **`http://afonsorodrigues.com/pinga-ana-adventure-demo/`** (e HTTPS quando activares **Enforce HTTPS** no repo `.github.io`).

## Sem `USER_SITE_REPO` (só GitHub Pages deste repo)

Com a variable **vazia / não definida**, o fluxo antigo mantém-se: artefacto → **Deploy pygbag to GitHub Pages** → URL `https://<user>.github.io/pinga-ana-adventure-demo/`.

## Build local

```bash
pip install -r requirements.txt
python -m pygbag --build .
```

Saída em `build/web/`.
