# lince.sh

Website for the [LINCE](https://github.com/RisorseArtificiali/lince) project.

Static HTML + Tailwind CDN. Hosted on GitHub Pages.

## Local preview

```bash
python3 -m http.server 8000
# Open http://localhost:8000
```

## Deploy

Pushed to `main` and deployed automatically via GitHub Pages (Settings > Pages > Source: Deploy from branch `main`, root `/`).

## Custom domain

The `CNAME` file points to `lince.sh`. DNS must have:
- A records pointing to GitHub Pages IPs
- Or CNAME record pointing to `risorseartificiali.github.io`
