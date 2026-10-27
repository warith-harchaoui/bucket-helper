# Exemples Bucket Helper

Recettes pratiques pour `bucket-helper` face à **AWS S3 et tout stockage
compatible S3** (MinIO, Cloudflare R2, Backblaze B2, DigitalOcean Spaces,
Wasabi, etc.). Chaque extrait ci-dessous part des imports et de la source
d'identifiants décrits dans [Mise en place](#mise-en-place) : vous pouvez
donc sauter directement à la section qui vous intéresse.

Chaque appel présenté ici atteint un bucket, donc chaque appel demande des
identifiants. Rien n'a été lancé contre un stockage réel : les extraits
Python ont été vérifiés contre les signatures de `bucket_helper/main.py`,
aucune sortie n'est donc affichée pour eux. La sortie réellement capturée
se trouve dans [Ligne de commande](#ligne-de-commande), où `--help` et
`strip-path` répondent sans ouvrir de connexion.

---

## Table des matières

1. [Mise en place](#mise-en-place)
2. [Charger les identifiants](#charger-les-identifiants)
3. [Envoyer / récupérer / supprimer](#envoyer--récupérer--supprimer)
4. [Existence et listage](#existence-et-listage)
5. [Buckets : création à la demande](#buckets--création-à-la-demande)
6. [Clés distantes temporaires (nettoyage automatique)](#clés-distantes-temporaires-nettoyage-automatique)
7. [Points d'accès compatibles S3 (MinIO / R2 / B2 / Spaces / Wasabi)](#points-daccès-compatibles-s3-minio--r2--b2--spaces--wasabi)
8. [Composition avec sftp-helper / os-helper](#composition-avec-sftp-helper--os-helper)
9. [Ligne de commande](#ligne-de-commande)
10. [Dépannage](#dépannage)

---

## Mise en place

```bash
pip install --force-reinstall --no-cache-dir \
    bucket-helper
```

La CLI est livrée avec cette installation de base. La surface HTTP et le
serveur MCP sont des extras :

```bash
pip install "bucket-helper[api]"       # surface HTTP FastAPI
pip install "bucket-helper[mcp]"       # serveur MCP (entraîne [api])
```

Chaque extrait Python ci-dessous suppose ces deux imports :

```python
import bucket_helper as bh
import os_helper as osh
```

…ainsi qu'une source de configuration portant au minimum
`s3_access_key`, `s3_secret_key`, `s3_bucket` et `s3_https` : un
`settings.yaml`, un `.env` ou les variables d'environnement
correspondantes. Voir le README pour la liste complète des clés ainsi que
le tableau des points d'accès par fournisseur.

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

# Envoi sans destination : nom aléatoire unique sous cred["s3_prefix"]
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

# Forme clé nue (se résout sous cred["s3_bucket"])
if bh.exists("invoices/2026/06.pdf", cred):
    print("same check, shorter")

# Liste les clés sous un préfixe (jusqu'à max_keys, 1000 par défaut).
# Les clés arrivent dans l'ordre lexicographique de S3, sans tri côté client.
for key in bh.list_prefix("invoices/2026/", cred, max_keys=200):
    print(key)
```

`list_prefix` s'arrête à `max_keys` sans pouvoir dire s'il s'est arrêté
trop tôt : 200 clés ont la même allure, que le préfixe contienne exactement
200 objets ou vingt mille. Dès qu'un programme — et non un humain — agit
sur la liste, demandez cette information en plus :

```python
keys, tronque = bh.list_prefix_page("invoices/2026/", cred, max_keys=200)
if tronque:
    print("plus de 200 factures sous ce préfixe ; augmentez max_keys")
```

La fonction demande à S3 une clé au-delà du plafond puis indique si elle est
arrivée : le surcoût est d'une seule clé.

Pour des listages encore plus volumineux, descendez au paginateur boto3
brut via `bh.get_client_s3(cred)`, qui est un context manager :

```python
with bh.get_client_s3(cred) as s3:
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cred["s3_bucket"], Prefix="invoices/"):
        for obj in page.get("Contents") or []:
            print(obj["Key"], obj["Size"])
```

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
    "s3_access_key": "minioadmin",
    "s3_secret_key": "minioadmin",
    "s3_bucket": "uploads",
    "s3_https": "http://minio.example.com:9000/uploads",
    "s3_endpoint_url": "http://minio.example.com:9000",
    "s3_use_path_style": "true",
    "s3_region": "us-east-1",  # MinIO accepte n'importe quelle chaîne de région
}

bh.make_bucket("uploads", cred)
bh.upload("file.bin", cred, "file.bin")
```

Les valeurs par fournisseur sont listées dans le
[README](README.md#endpoint-urls-for-common-s3-compatible-storage).

## Composition avec sftp-helper / os-helper

Miroir d'un envoi entre un stockage de type AWS et une boîte de dépôt SFTP
partenaire. `sftp-helper` est un paquet distinct (`pip install
sftp-helper`) ; un même `settings.yaml` peut porter les deux jeux
d'identifiants, puisque chaque loader ne lit que les clés qu'il déclare :

```python
import os_helper as osh
import bucket_helper as bh
import sftp_helper as sftph

# Un seul réglage de journalisation pour toute la suite ; les deux helpers y passent.
osh.verbosity(2)

s3_cred = bh.credentials("path/to/settings.yaml")
sftp_cred = sftph.credentials("path/to/settings.yaml")

# Archive de long terme sur S3
s3_uri = bh.upload("report.pdf", s3_cred, "reports/2026-06.pdf")
# Miroir vers le partenaire SFTP
sftph.upload("report.pdf", sftp_cred, "/inbox/2026-06.pdf")

print(f"Archived at {s3_uri}; delivered to SFTP partner.")
```

## Ligne de commande

Une seule ligne de commande, `bucket-helper`, construite avec click. Huit
verbes, les mêmes huit que ceux exposés par la surface HTTP :

```console
$ bucket-helper --help
Usage: bucket-helper [OPTIONS] COMMAND [ARGS]...

  Bucket Helper — S3-compatible object storage from the shell.

Options:
  -V, --version  Show the version and exit.
  -h, --help     Show this message and exit.

Commands:
  delete       Delete an S3 object (idempotent).
  download     Download an S3 object to a local path.
  exists       Return exit code 0 if the object exists, 1 otherwise.
  list         List keys under a prefix in the default bucket.
  make-bucket  Create a bucket (no-op if it already exists).
  strip-path   Extract the key part of an 's3://bucket/key' address.
  tempfile     Emit a unique random key + public URL (JSON).
  upload       Upload a local file to S3.
```

Chaque verbe accepte `--config`, qui pointe sur un `settings.yaml` (ou sur
un dossier qui en contient un) ; en l'omettant, le repli se fait sur `.env`
puis l'environnement :

```bash
bucket-helper upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config settings.yaml --key folder/uploaded.txt
bucket-helper download    --config settings.yaml --key folder/uploaded.txt --output back.txt
bucket-helper list        --config settings.yaml --prefix folder/ --max-keys 200
bucket-helper delete      --config settings.yaml --key folder/uploaded.txt
bucket-helper make-bucket --config settings.yaml --bucket new-bucket
bucket-helper tempfile    --config settings.yaml --ext json --prefix runs
bucket-helper strip-path  --config settings.yaml --address s3://my-bucket/path/to/obj
```

`strip-path` ne fait que du traitement de chaîne : c'est le seul verbe qui
répond sans toucher au réseau. Ici les identifiants viennent de
l'environnement plutôt que d'un fichier, d'où l'absence de `--config` :

```console
$ bucket-helper strip-path --address s3://my-bucket/path/to/obj
path/to/obj
```

Deux comportements à connaître avant de glisser tout cela dans un script :

- `exists` affiche `true` / `false` **et** sort en 1 quand l'objet est
  absent, de sorte que `if bucket-helper exists …; then` fonctionne
  directement.
- `list` plafonne à `--max-keys` (1000 par défaut) et, lorsqu'il touche ce
  plafond, émet un avertissement sur **stderr** pendant que les clés
  restent sur stdout : les pipelines ne sont pas perturbés et un `xargs`
  sur la sortie ne rate plus silencieusement des objets.

## Dépannage

| Symptôme | Cause | Correctif |
|---|---|---|
| `RuntimeError: Missing required keys for 'S3' configuration in files, .env files, or environment variables.` | aucune source n'a résolu les quatre clés requises — le message ne dit pas laquelle manque | pointez `--config` sur le fichier ou exportez `s3_access_key`, `s3_secret_key`, `s3_bucket` et `s3_https` |
| Les requêtes vers un MinIO derrière un domaine custom échouent à l'authentification | l'adressage par défaut est virtual-hosted (`bucket.endpoint/key`), ce déploiement attend `endpoint/bucket/key` | réglez `s3_use_path_style: "true"` |
| La vérification TLS échoue contre un MinIO de développement | certificat auto-signé | réglez `s3_verify_ssl: "false"` — pour un hôte que vous maîtrisez, nulle part ailleurs |
| `ModuleNotFoundError: No module named 'bucket_helper.cli_argparse'` | un script `bucket-helper` laissé par une installation antérieure à la `v1.3.0`, qui pointe sur un module disparu | réinstallez : `pip install --force-reinstall bucket-helper` |
| Un listage renvoie exactement `--max-keys` clés sans qu'on sache si c'était tout | `list_prefix` ne signale pas son propre plafond | utilisez `list_prefix_page` ou lisez l'avertissement que `bucket-helper list` écrit sur stderr |
