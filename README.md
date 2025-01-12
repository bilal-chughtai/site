# bilal's website

site infra mostly written by [rudolf](https://github.com/LRudL/site).

**setup**

- `python3 -m venv venv`
- `source venv/bin/activate`
- `pip install -r requirements.txt`
- `python -m build` (or `chmod +x autoreload.sh` and `./autoreload.sh` to autoreload build)
- `python -m http.server` and navigate to `out/index.html`