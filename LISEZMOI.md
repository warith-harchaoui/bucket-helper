# Bucket Helper

[🇫🇷](https://github.com/warith-harchaoui/bucket-helper/blob/main/LISEZMOI.md) · [🇬🇧](https://github.com/warith-harchaoui/bucket-helper/blob/main/README.md)

[![CI](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml/badge.svg)](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml) [![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://github.com/warith-harchaoui/bucket-helper/blob/main/LICENSE) [![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](#)

`Bucket Helper` fait partie d'une collection de bibliothèques appelée `AI Helpers`, développée pour bâtir des applications d'intelligence artificielle.

Fonctions utilitaires pour **AWS S3** et tout **stockage objet compatible S3** : MinIO, Backblaze B2 (API S3), DigitalOcean Spaces, Cloudflare R2, Wasabi. Bâti sur [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). Même forme que [sftp-helper](https://github.com/warith-harchaoui/sftp-helper) : un loader `credentials()`, les opérations CRUD habituelles (`upload` / `download` / `delete` / `exists` / `list_prefix`) et un context manager `remote_tempfile` pour le stage-and-share.

[🌍 AI Helpers](https://harchaoui.org/warith/ai-helpers)

[![logo](https://raw.githubusercontent.com/warith-harchaoui/bucket-helper/main/assets/logo.png)](https://harchaoui.org/warith/ai-helpers)

## La promesse

**Distant par conception.** `bucket-helper` existe pour déplacer des données
vers et depuis le stockage objet *de votre choix* : AWS ou tout point de
terminaison compatible S3 que vous lui indiquez (y compris une instance MinIO
sur votre propre réseau). Il n'est donc volontairement **pas** local-first et
ne fournit **aucune interface graphique**. Pour un distant joint en SFTP
plutôt qu'en S3, utilisez `sftp-helper` ; pour télécharger un média depuis une
URL, utilisez `youtube-helper`.

## Documentation

[💻 Documentation](https://harchaoui.org/warith/ai-helpers/docs/bucket-helper-doc/)

[🗺️ Paysage](https://github.com/warith-harchaoui/bucket-helper/blob/main/PAYSAGE.md)

[📋 Exemples](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXEMPLES.md)

[🎯 Déclencheurs](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md)

## Fonctionnalités

- **CRUD** contre AWS S3 ou tout point de terminaison compatible S3 :
  `upload`, `download`, `delete`, `exists`, `list_prefix`.
- **Fonctionne avec n'importe quel fournisseur compatible S3** : MinIO,
  Backblaze B2 (API S3), DigitalOcean Spaces, Cloudflare R2, Wasabi, en
  pointant l'identifiant `endpoint_url` dessus ; aucun changement de code par
  fournisseur.
- **Chargeur d'identifiants** (`credentials`) résolvant JSON / YAML /
  variables d'environnement / `.env`, dans cet ordre de repli.
- **Context manager `remote_tempfile`** pour le stage-and-share : upload,
  retourne l'objet, suppression automatique à la sortie du bloc, aucun
  nettoyage manuel.
- **Trois surfaces, un seul comportement** : bibliothèque Python, CLI
  argparse, jumeau CLI click (extra `[cli]`) et surface HTTP FastAPI (extra
  `[api]`). Voir la [section multi-surface](#exposition-multi-surfaces).
- **Image Docker** livre le serveur HTTP prêt à l'emploi.

## Installation

**Prérequis** : **Python 3.10–3.13** et **git**, multiplateforme :

- 🍎 **macOS** ([Homebrew](https://brew.sh)) : `brew install python git`
- 🐧 **Ubuntu/Debian** : `sudo apt update && sudo apt install -y python3 python3-pip git`
- 🪟 **Windows** (PowerShell) : `winget install Python.Python.3.12 Git.Git`

On recommande de travailler dans un environnement Python. Si vous ne savez pas en créer un, voir [🥸 Tech tips](https://harchaoui.org/warith/4ml/#install).

### Depuis PyPI (recommandé)

```bash
# Bibliothèque principale (loader credentials + CRUD + remote_tempfile)
pip install bucket-helper

# Surfaces optionnelles
pip install "bucket-helper[cli]"       # variante CLI click
pip install "bucket-helper[api]"       # surface HTTP FastAPI
```

### Depuis les sources (sans PyPI)

```bash
# Bibliothèque principale
pip install bucket-helper

# Surfaces optionnelles
pip install "bucket-helper[cli]"
pip install "bucket-helper[api]"
```

La CLI argparse est toujours disponible. L'extra `[cli]` ajoute la variante click.

## Configuration

Un template prêt à remplir est committé dans [`settings.yaml.example`](https://github.com/warith-harchaoui/bucket-helper/blob/main/settings.yaml.example). Copiez-le en `settings.yaml` et éditez-le sur place : `settings.yaml` est gitignored, donc pas de secret committé par accident :

```bash
cp settings.yaml.example settings.yaml
# puis éditez settings.yaml avec vos identifiants AWS / MinIO / R2 / B2
```

Vous pouvez aussi écrire du JSON plutôt que du YAML, utiliser un `.env` ou définir des variables d'environnement : `bucket-helper` les essaie dans cet ordre via `os_helper.get_config`. Clés requises :

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
| `s3_endpoint_url` | vide (= AWS S3) | À renseigner pour les backends S3-compatibles : voir tableau ci-dessous |
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

## Utilisation

Pour le catalogue complet d'exemples (uploads / téléchargements / listages, endpoints S3-compatibles tels que MinIO / R2 / B2 / Spaces / Wasabi, clés distantes temporaires à nettoyage automatique, miroir avec sftp-helper), voir [📋 EXEMPLES.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXEMPLES.md).

```python
import bucket_helper as bh

# Charger les identifiants : JSON / YAML / env / .env (repli automatique dans cet ordre)
cred = bh.credentials("path/to/settings.yaml")

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

Déposez un fichier généré sous une clé aléatoire unique, passez l'URL publique à un worker / webhook en aval et l'objet est supprimé à la sortie du bloc (même si le corps lève une exception) :

```python
import bucket_helper as bh
import requests

cred = bh.credentials("path/to/settings.yaml")

with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    # Passer l'URL à un service qui la consomme une fois.
    requests.post("https://hook.example.com/process", json={"input_url": public_url}).raise_for_status()
# L'objet n'existe plus ici, pas de nettoyage manuel.
```

## Exposition multi-surfaces

Chaque fonction publique de la bibliothèque est aussi exposée en :

- **CLI argparse** : `bucket-helper <sous-commande>` (installée par défaut).
- **CLI click** : `bucket-helper-click <sous-commande>` (nécessite l'extra `[cli]`).
- **HTTP FastAPI** : `uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000` (extra `[api]`).
- **MCP** : `bucket-helper-mcp` expose la même surface HTTP comme outils MCP
  pour tout hôte agentique compatible (extra `[mcp]`).

Les deux CLI partagent les mêmes noms de sous-commandes et de flags ; prenez celle que vous préférez.

Le catalogue exhaustif de ce qui déclenche la boîte à outils (formulations en
langage naturel, commandes, fonctions, indices d'adresse, règles SKIP
explicites) se trouve dans [TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md).

## Exemples CLI

```bash
# CLI argparse (toujours disponible)
bucket-helper upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config settings.yaml --key folder/uploaded.txt
bucket-helper download    --config settings.yaml --key folder/uploaded.txt --output back.txt
bucket-helper list        --config settings.yaml --prefix folder/
bucket-helper delete      --config settings.yaml --key folder/uploaded.txt
bucket-helper make-bucket --config settings.yaml --bucket new-bucket
bucket-helper tempfile    --config settings.yaml --ext json --prefix runs
bucket-helper strip-path  --config settings.yaml --address s3://my-bucket/path/to/obj

# CLI click : mêmes verbes, mêmes flags
bucket-helper-click upload --config settings.yaml --input local.txt --key folder/uploaded.txt
```

## Serveur HTTP

```bash
# Sert HTTP (les credentials par défaut viennent de BUCKET_HELPER_CONFIG)
BUCKET_HELPER_CONFIG=$PWD/settings.yaml uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000
# → Swagger UI sur http://localhost:8000/docs
```

Les identifiants peuvent aussi être passés en form-fields multipart par
requête (`s3_access_key` / `s3_secret_key` / `s3_bucket` / `s3_https` / …).

## Docker

```bash
docker build -t bucket-helper .
docker run --rm -p 8000:8000 \
  -e BUCKET_HELPER_CONFIG=/config/settings.yaml \
  -v $PWD/settings.yaml:/config/settings.yaml:ro \
  bucket-helper
```

Voir aussi : [TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md) (ce qui invoque la boîte à outils) et
[GUI.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/GUI.md) (plan produit visuel ; aucune GUI n'est livrée, bucket-helper est de la plomberie de stockage objet distant).

## Auteur

 - [Warith HARCHAOUI](https://linkedin.com/in/warith-harchaoui)

## Remerciements

Remerciements chaleureux à [Mohamed Chelali](https://mchelali.github.io) et [Bachir Zerroug](https://www.linkedin.com/in/bachirzerroug) pour nos échanges fructueux.

## Licence

Ce projet est distribué sous licence BSD-3-Clause ; voir le fichier [LICENSE](https://github.com/warith-harchaoui/bucket-helper/blob/main/LICENSE) pour les détails.
