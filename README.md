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

## Build local

```bash
pip install -r requirements.txt
python -m pygbag --build .
```

Saída em `build/web/` (subir ou publicar só esse conteúdo se for deploy manual).
