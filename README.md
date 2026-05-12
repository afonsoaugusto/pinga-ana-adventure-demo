# pinga-ana-adventure-demo

Demo **pygame-ce** empacotada com **pygbag** (async + `await asyncio.sleep(0)` no loop).

## Se o site abrir em branco ou só mostrar este README

O deploy do jogo é feito pelo workflow **Deploy pygbag to GitHub Pages** (artefato em `build/web`). No repositório GitHub:

1. **Settings → Pages**
2. Em **Build and deployment**, em **Source**, escolha **GitHub Actions** (não “Deploy from a branch”).
3. Abra a aba **Actions**, confira se o workflow concluiu com sucesso e rode de novo se precisar.

Enquanto a origem for uma **branch** com `README.md` na raiz, o GitHub usa **Jekyll** e a URL mostra esta página estática — não o `index.html` do pygbag.

## Build local

```bash
pip install -r requirements.txt
python -m pygbag --build .
```

Saída em `build/web/` (subir ou publicar só esse conteúdo se for deploy manual).
