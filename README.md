# pinga-ana-adventure-demo

Demo **pygame-ce** empacotada com **pygbag** (async + `await asyncio.sleep(0)` no loop).

## Se o site abrir em branco ou só mostrar este README

O deploy do jogo é feito pelo workflow **Deploy pygbag to GitHub Pages** (artefato em `build/web`). No repositório GitHub:

1. **Settings → Pages**
2. Em **Build and deployment**, em **Source**, escolha **GitHub Actions** (não “Deploy from a branch”).
3. Abra a aba **Actions**, confira se o workflow concluiu com sucesso e rode de novo se precisar.

Enquanto a origem for uma **branch** com `README.md` na raiz, o GitHub usa **Jekyll** e a URL mostra esta página estática — não o `index.html` do pygbag.

## 404 em `https://afonsorodrigues.com/pinga-ana-adventure-demo/`

Isto costuma acontecer quando **Pages → Custom domain** neste repositório aponta o site para um host onde **já existe outro GitHub Pages no apex** (`https://afonsorodrigues.com/` com 200). O GitHub faz **301** de `https://<user>.github.io/pinga-ana-adventure-demo/` para esse URL com **subcaminho**, mas **não publica o projeto nesse path** nesse cenário — daí o **404**.

**Correção (escolha uma):**

1. **URL padrão do GitHub (mais simples)**  
   Em **Settings → Pages → Custom domain**, **apague** o domínio personalizado deste repositório (ou use “Remove”).  
   O jogo fica em: `https://afonsoaugusto.github.io/pinga-ana-adventure-demo/`

2. **Manter o teu domínio**  
   Cria um **subdomínio** (ex.: `pinga.afonsorodrigues.com` ou `jogo.afonsorodrigues.com`): no DNS, **CNAME** desse nome para `<user>.github.io`.  
   Em **Pages** deste repo, define **Custom domain** com esse **subdomínio** (não uses o apex + `/pinga-ana-adventure-demo/` como URL “oficial” do GitHub para este site).

Ativa também **Enforce HTTPS** em Pages quando o certificado estiver pronto.

### “Não consigo mudar” `https://afonsorodrigues.com/pinga-ana-adventure-demo/`

Esse endereço **não se edita à mão**: o GitHub monta-o quando há **domínio personalizado** no apex (`afonsorodrigues.com`) ligado à conta ou organização e um repositório de projeto com Pages. O que podes fazer é **mudar a origem do domínio**, não o texto do URL no ecrã.

1. **Neste repositório:** **Settings → Pages → Custom domain** → apaga o valor → **Save** (ou **Remove**). Se o campo estiver vazio mas o site ainda mostrar o domínio, o domínio pode estar noutro sítio (passos 2–3).
2. **Conta pessoal:** repositório **`afonsoaugusto.github.io`** (se existir) → **Settings → Pages** → rever **Custom domain** e ficheiro **`CNAME`** na raiz do branch que publica.
3. **Organização:** como **owner**, **Organization settings → Pages** → rever domínio e “Verified domains”; um domínio a nível de org aplica-se a vários repositórios.
4. Depois de remover o apex deste fluxo, o link que **funciona** passa a ser só o padrão: `https://afonsoaugusto.github.io/pinga-ana-adventure-demo/` (podes partilhar/bookmark este).

Para continuares a usar **afonsorodrigues.com** com o jogo, a solução estável é **subdomínio** (ex.: `pinga.afonsorodrigues.com` com CNAME para `afonsoaugusto.github.io`) e esse nome em **Custom domain** **neste** repo — não o path `/pinga-ana-adventure-demo/` no apex.

## Build local

```bash
pip install -r requirements.txt
python -m pygbag --build .
```

Saída em `build/web/` (subir ou publicar só esse conteúdo se for deploy manual).
