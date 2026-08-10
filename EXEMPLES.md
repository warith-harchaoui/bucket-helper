# Exemples Bucket Helper

Recettes pratiques pour `bucket-helper` face à **AWS S3 et tout stockage
compatible S3** (MinIO, Cloudflare R2, Backblaze B2, DigitalOcean Spaces,
Wasabi, etc.). Chaque extrait suppose :

```python
import bucket_helper as bh
import os_helper as osh
```

et l'existence d'une source de configuration (`settings.yaml`, `.env` ou
variables d'environnement `S3_*`) : voir le README pour les clés requises
et le tableau des points d'accès par fournisseur.

---

## Sommaire

1. [Mise en place](#mise-en-place)
2. [Charger les identifiants](#charger-les-identifiants)
3. [Envoyer / récupérer / supprimer](#envoyer--recuperer--supprimer)
4. [Existence et listage](#existence-et-listage)
5. [Buckets : création à la demande](#buckets--creation-a-la-demande)
6. [Clés distantes temporaires (nettoyage automatique)](#cles-distantes-temporaires-nettoyage-automatique)
7. [Points d'accès compatibles S3 (MinIO / R2 / B2 / Spaces / Wasabi)](#points-dacces-compatibles-s3-minio--r2--b2--spaces--wasabi)
8. [Composition avec sftp-helper / os-helper](#composition-avec-sftp-helper--os-helper)

---

## Mise en place

```bash
pip install --force-reinstall --no-cache-dir \
    bucket-helper
```

En dessous, `bucket-helper` est une fine couche par-dessus
[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).
Tout ce qui parle l'API S3 d'AWS fonctionne : réglez `s3_endpoint_url` pour
les fournisseurs non AWS.

## Charger les identifiants

```python
# Fichier YAML / JSON (à privilégier en exploitation)
cred = bh.credentials("path/to/settings.yaml")

# Repli sur .env / variables d'environnement S3_*
cred = bh.credentials()
```

Les clés optionnelles (`s3_region`, `s3_endpoint_url`, `s3_prefix`,
`s3_use_path_style`, `s3_verify_ssl`) sont récupérées au mieux depuis les
mêmes sources : voir le tableau des points d'accès par fournisseur dans le
README.

## Envoyer / récupérer / supprimer

```python
# Envoi : clé de destination sous le bucket par défaut
uri = bh.upload("invoice.pdf", cred, "invoices/2026/06.pdf")
# uri == "s3://my-bucket/invoices/2026/06.pdf"

# Envoi sans destination : nom haché par contenu sous cred["s3_prefix"]
uri = bh.upload("snapshot.bin", cred)
# uri == "s3://my-bucket/<random_hex>.bin"

# Envoi avec type MIME explicite (par défaut : deviné par boto3 / le serveur)
bh.upload("page.html", cred, "site/index.html", content_type="text/html")

# Récupération
bh.download("s3://my-bucket/invoices/2026/06.pdf", "06.pdf", cred)

# Suppression : idempotente (renvoie toujours True si l'objet a bien disparu après l'appel)
bh.delete("s3://my-bucket/invoices/2026/06.pdf", cred)
```

Vous pouvez mélanger adresses `"s3://bucket/key"` et clés nues `"key"` :
les clés nues se résolvent sous `cred["s3_bucket"]`.

## Existence et listage

```python
if bh.exists("s3://my-bucket/invoices/2026/06.pdf", cred):
    print("invoice already uploaded")
    # invoice already uploaded

# Forme clé nue (se résout sous cred["s3_bucket"])
if bh.exists("invoices/2026/06.pdf", cred):
    print("same check, shorter")
    # same check, shorter

# Liste les clés sous un préfixe (jusqu'à max_keys, 1000 par défaut)
for key in bh.list_prefix("invoices/2026/", cred, max_keys=200):
    print(key)
    # invoices/2026/01.pdf
    # invoices/2026/02.pdf
    # ...
```

Pour des listages plus volumineux, descendez au paginateur boto3 brut via
`bh.get_client_s3(cred)`.

## Buckets : création à la demande

`make_bucket` est idempotente et respecte `cred["s3_region"]` (pas de
`LocationConstraint` pour `us-east-1`, une particularité d'AWS) :

```python
bh.make_bucket("ephemeral-uploads", cred)
```

## Clés distantes temporaires (nettoyage automatique)

`remote_tempfile` réserve une clé aléatoire unique dans le bucket par
défaut et supprime l'objet à la sortie du bloc, même en cas d'exception.
Utile pour les flux d'échange temporaire (envoyer, transmettre l'URL
publique à un consommateur en aval, nettoyer) :

```python
import requests

cred = bh.credentials("path/to/settings.yaml")

with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    requests.post(
        "https://hook.example.com/process",
        json={"input_url": public_url},
    ).raise_for_status()
# L'objet a disparu ici, aucun nettoyage manuel à faire.
```

`public_url` est construite à partir de `cred["s3_https"]` : réglez cette
clé sur le CDN ou sur le nom d'hôte public du bucket selon votre topologie.

## Points d'accès compatibles S3 (MinIO / R2 / B2 / Spaces / Wasabi)

Réglez `s3_endpoint_url` sur le dictionnaire d'identifiants et, pour MinIO
en particulier, `s3_use_path_style=true` :

```python
cred = {
    "s3_access_key":      "minioadmin",
    "s3_secret_key":      "minioadmin",
    "s3_bucket":          "uploads",
    "s3_https":           "http://minio.example.com:9000/uploads",
    "s3_endpoint_url":    "http://minio.example.com:9000",
    "s3_use_path_style":  "true",
    "s3_region":          "us-east-1",  # MinIO accepte n'importe quelle chaîne de région
}

bh.make_bucket("uploads", cred)
bh.upload("file.bin", cred, "file.bin")
```

Les valeurs par fournisseur sont listées dans le
[README](README.md#endpoint-urls-for-common-s3-compatible-storage).

## Composition avec sftp-helper / os-helper

Miroir d'un envoi entre un stockage de type AWS et une boîte de dépôt SFTP
partenaire :

```python
import os_helper as osh
import bucket_helper as bh
import sftp_helper as sftph

osh.verbosity(2)

s3_cred  = bh.credentials("path/to/settings.yaml")
sftp_cred = sftph.credentials("path/to/settings.yaml")

# Archive de long terme sur S3
s3_uri = bh.upload("report.pdf", s3_cred, "reports/2026-06.pdf")
# Miroir vers le partenaire SFTP
sftph.upload("report.pdf", sftp_cred, "/inbox/2026-06.pdf")

print(f"Archived at {s3_uri}; delivered to SFTP partner.")
# Archived at s3://my-bucket/reports/2026-06.pdf; delivered to SFTP partner.
```
