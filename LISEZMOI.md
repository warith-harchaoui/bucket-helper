# Bucket Helper

[🇫🇷](LISEZMOI.md) · [🇬🇧](README.md)

[![CI](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml/badge.svg)](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml) [![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](#)

`Bucket Helper` fait partie d'une collection de bibliothèques appelée `AI Helpers`, développée pour bâtir des applications d'intelligence artificielle.

Fonctions utilitaires pour **AWS S3** et tout **stockage objet compatible S3** — MinIO, Backblaze B2 (API S3), DigitalOcean Spaces, Cloudflare R2, Wasabi, et compagnie. Bâti sur [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). Même forme que [sftp-helper](https://github.com/warith-harchaoui/sftp-helper) : un loader `credentials()`, les opérations CRUD habituelles (`upload` / `download` / `delete` / `exists` / `list_prefix`), et un context manager `remote_tempfile` pour des flux stage-and-share.

[🌍 AI Helpers](https://harchaoui.org/warith/ai-helpers)

[![logo](assets/logo.png)](https://harchaoui.org/warith/ai-helpers)

# Documentation

[💻 Documentation](https://harchaoui.org/warith/ai-helpers/docs/bucket-helper-doc/)

[📋 Exemples](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXAMPLES.md)

# Installation

**Prérequis** — **Python 3.10–3.13** et **git**, multiplateforme :

- 🍎 **macOS** ([Homebrew](https://brew.sh)) : `brew install python git`
- 🐧 **Ubuntu/Debian** : `sudo apt update && sudo apt install -y python3 python3-pip git`
- 🪟 **Windows** (PowerShell) : `winget install Python.Python.3.12 Git.Git`

Puis installer le paquet :


```bash
pip install --force-reinstall --no-cache-dir git+https://github.com/warith-harchaoui/bucket-helper.git@v0.2.2
```

Extras optionnels — installez ce dont vous avez besoin :

```bash
# La CLI argparse est toujours disponible. Ajoutez la variante click :
pip install 'bucket-helper[cli] @ git+https://github.com/warith-harchaoui/bucket-helper.git@v0.2.2'

# Serveur HTTP (FastAPI + uvicorn + python-multipart) :
pip install 'bucket-helper[api] @ git+https://github.com/warith-harchaoui/bucket-helper.git@v0.2.2'

# Outils MCP (fastapi-mcp) — nécessite la plomberie [api] :
pip install 'bucket-helper[api,mcp] @ git+https://github.com/warith-harchaoui/bucket-helper.git@v0.2.2'
```

# Configuration

Un template prêt-à-remplir est committé dans [`s3_config.json.example`](s3_config.json.example). Copiez-le en `s3_config.json` et éditez-le sur place — les vrais `*config.json` sont gitignored donc impossible de committer des secrets par accident :

```bash
cp s3_config.json.example s3_config.json
# puis éditez s3_config.json avec vos identifiants AWS / MinIO / R2 / B2
```

Vous pouvez aussi écrire un `s3_config.yaml`, utiliser un `.env`, ou définir des variables d'environnement — `bucket-helper` essaie dans cet ordre via `os_helper.get_config`.


Écrivez un `s3_config.json`, un `s3_config.yaml`, un `.env`, ou utilisez des variables d'environnement. Clés requises :

```json
{
  "s3_access_key": "AKIA...",
  "s3_secret_key": "...",
  "s3_bucket":     "my-bucket",
  "s3_https":      "https://my-bucket.s3.eu-west-3.amazonaws.com"
}
```

Clés optionnelles :

| Clé | Défaut | Notes |
|---|---|---|
| `s3_region` | `"us-east-1"` | Région AWS ; cosmétique pour MinIO / R2 |
| `s3_endpoint_url` | vide (= AWS S3) | À renseigner pour les backends S3-compatibles — voir tableau ci-dessous |
| `s3_prefix` | vide | Préfixe par défaut ajouté par `upload(...)` quand aucune destination n'est fournie |
| `s3_use_path_style` | `"false"` | Forcer l'adressage path-style (`endpoint/bucket/key` plutôt que `bucket.endpoint/key`). Typique pour MinIO avec domaines custom. |
| `s3_verify_ssl` | `"true"` | À désactiver uniquement en dev MinIO avec certs auto-signés |

## URLs d'endpoint pour les stockages S3-compatibles courants

Mettez `s3_endpoint_url` à :

| Fournisseur | Endpoint |
|---|---|
| **AWS S3** | laisser vide / non défini |
| **MinIO** | `http://minio.example.com:9000` (ou `https://...` avec TLS) |
| **DigitalOcean Spaces** | `https://nyc3.digitaloceanspaces.com` (région dans le sous-domaine) |
| **Cloudflare R2** | `https://<account_id>.r2.cloudflarestorage.com` |
| **Backblaze B2 (API S3)** | `https://s3.<region>.backblazeb2.com` |
| **Wasabi** | `https://s3.<region>.wasabisys.com` |

# Utilisation

Pour le catalogue complet d'exemples (uploads / téléchargements / listages, endpoints S3-compatibles — MinIO / R2 / B2 / Spaces / Wasabi, clés distantes temporaires avec auto-nettoyage, miroir avec sftp-helper), voir [📋 EXAMPLES.md](EXAMPLES.md).

```python
import bucket_helper as bh

# Charger les identifiants — JSON / YAML / env / .env (repli automatique dans cet ordre)
cred = bh.credentials("path/to/s3_config.json")

# Uploader un fichier local
uri = bh.upload("local.txt", cred, "folder/uploaded.txt")
# uri == "s3://my-bucket/folder/uploaded.txt"

assert bh.exists(uri, cred)

# Télécharger
bh.download(uri, "downloaded.txt", cred)

# Lister
for key in bh.list_prefix("folder/", cred):
    print(key)

# Supprimer
bh.delete(uri, cred)
```

## Exemple MinIO

```python
cred = {
    "s3_access_key":      "minioadmin",
    "s3_secret_key":      "minioadmin",
    "s3_bucket":          "uploads",
    "s3_https":           "http://minio.example.com:9000/uploads",
    "s3_endpoint_url":    "http://minio.example.com:9000",
    "s3_use_path_style":  "true",
    "s3_region":          "us-east-1",  # MinIO accepte n'importe quelle région
}

bh.make_bucket("uploads", cred)
bh.upload("file.bin", cred, "file.bin")
```

## Stage-and-share avec `remote_tempfile`

Déposez un fichier généré à une clé aléatoire unique, passez l'URL publique à un worker / webhook en aval, et l'objet est supprimé à la sortie du bloc (même si le corps lève une exception) :

```python
import bucket_helper as bh
import requests

cred = bh.credentials("path/to/s3_config.json")

with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    # Passer l'URL à un service qui la consomme une fois.
    requests.post("https://hook.example.com/process", json={"input_url": public_url}).raise_for_status()
# L'objet n'existe plus ici, pas de nettoyage manuel.
```

# Exposition multi-surfaces

Chaque fonction publique de la bibliothèque est aussi exposée en :

- **CLI argparse** — `bucket-helper <sous-commande>` (installée par défaut).
- **CLI click** — `bucket-helper-click <sous-commande>` (nécessite l'extra `[cli]`).
- **HTTP FastAPI** — `uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000` (extra `[api]`).
- **Outils MCP** — `bucket-helper-mcp` (extras `[api,mcp]`).

Les deux CLI partagent les mêmes noms de sous-commandes et de flags — choisissez votre préférée.

## Exemples CLI

```bash
# CLI argparse (toujours disponible)
bucket-helper upload      --config s3_config.json --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config s3_config.json --key folder/uploaded.txt
bucket-helper download    --config s3_config.json --key folder/uploaded.txt --output back.txt
bucket-helper list        --config s3_config.json --prefix folder/
bucket-helper delete      --config s3_config.json --key folder/uploaded.txt
bucket-helper make-bucket --config s3_config.json --bucket new-bucket
bucket-helper tempfile    --config s3_config.json --ext json --prefix runs
bucket-helper strip-path  --config s3_config.json --address s3://my-bucket/path/to/obj

# CLI click — mêmes verbes, mêmes flags
bucket-helper-click upload --config s3_config.json --input local.txt --key folder/uploaded.txt
```

## Serveur HTTP + MCP

```bash
# Sert HTTP + MCP (les credentials par défaut viennent de BUCKET_HELPER_CONFIG)
BUCKET_HELPER_CONFIG=$PWD/s3_config.json bucket-helper-mcp

# Ou lancez uniquement FastAPI :
uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000
# → Swagger UI sur http://localhost:8000/docs
```

Les identifiants peuvent aussi être passés en form-fields multipart par
requête (`s3_access_key` / `s3_secret_key` / `s3_bucket` / `s3_https` / …).

## Docker

```bash
docker build -t bucket-helper .
docker run --rm -p 8000:8000 \
  -e BUCKET_HELPER_CONFIG=/config/s3_config.json \
  -v $PWD/s3_config.json:/config/s3_config.json:ro \
  bucket-helper
```

Voir aussi : [LANDSCAPE.md](LANDSCAPE.md) (positionnement compétitif) et
[GUI.md](GUI.md) (plan produit visuel).

# Auteur
 - [Warith HARCHAOUI](https://linkedin.com/in/warith-harchaoui)

# Remerciements
Remerciements chaleureux à [Mohamed Chelali](https://mchelali.github.io) et [Bachir Zerroug](https://www.linkedin.com/in/bachirzerroug) pour nos échanges fructueux.
