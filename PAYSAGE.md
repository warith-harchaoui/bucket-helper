# Paysage

🇫🇷 Français · [🇬🇧 LANDSCAPE.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/LANDSCAPE.md)

Bibliothèques et CLI Python voisines et concurrentes dans l'espace
« dialoguer avec du stockage objet compatible S3 », comparées à
`bucket-helper`. Les notes vont de ⭐ (1) à ⭐⭐⭐⭐⭐ (5), évaluées sur la
tâche visée par `bucket-helper` — la plomberie quotidienne du stockage
objet pour les pipelines d'IA et de données (identifiants par fichier de
configuration, upload / download / list / exists / delete, support du
mode chemin pour MinIO / R2 / B2 / Spaces / Wasabi, clés temporaires de
stage-and-share à nettoyage automatique). Une bibliothèque optimisée
pour un tout autre usage (par ex. un SDK bas niveau, une CLI native
d'un fournisseur) n'est pas pénalisée — la note reflète seulement
l'adéquation à *ce* créneau.

## En un coup d'œil

<!-- TABLE:START -->
| Stockage objet | Multi-fournisseur S3 | Identifiants par fichier de config | CRUD simple | Clés temporaires en attente-partage | URL compatibles S3 | Multi-surface | Installation légère | Ergonomie pipeline IA |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **bucket-helper** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| boto3 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| botocore | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| minio | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| s3fs | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| cloudpathlib | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| smart_open | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| apache-libcloud | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| awscli | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| gsutil | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| fsspec | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
<!-- TABLE:END -->

## Carte de positionnement

<!-- FIGURE:START -->
Représentation 2D du tableau ci-dessus.

![Carte de positionnement](https://raw.githubusercontent.com/warith-harchaoui/bucket-helper/main/assets/paysage.png)

La carte est un résumé en 2D des 8 critères : à lire comme une forme, pas comme un classement. « bucket-helper » se situe dans le coin en haut à droite. Les axes se lisent **Horizontal — Économie ↔ Flexibilité** et **Vertical — Simplicité ↔ Intelligence**.
<!-- FIGURE:END -->

## Positionnement

`bucket-helper` se place volontairement à l'intersection de
l'**ergonomie de `sftp-helper`** (identifiants par fichier de
configuration avec repli JSON / YAML / .env, chargeur `credentials()`
uniforme, API en mode chemin, nettoyage automatique via
`remote_tempfile`) et de la **portée de `boto3`** (parle à n'importe
quel endpoint compatible S3, pas seulement AWS). C'est une couche de
productivité *au-dessus* de boto3, pas un remplacement : on peut
toujours redescendre au `boto3` brut via `get_client_s3(cred)` dès qu'on
a besoin d'un paginateur, d'une URL présignée ou d'un réglage de
chiffrement côté serveur que l'utilitaire n'enveloppe pas.

Cette boîte à outils est du **stockage objet distant par conception** —
il n'y a ni mode local-first ni GUI. Elle existe pour déplacer des
octets vers et depuis un bucket, pas pour remplacer le disque.

Le principal différenciateur face à `boto3` seul tient en trois points :
(a) le chargeur de configuration unifie les sources d'identifiants —
JSON, YAML, `.env`, variables d'environnement — sur une flotte de
backends de stockage, sous une seule API en forme de dict ; (b) le
context manager `remote_tempfile` supprime le piège « ai-je oublié de
supprimer ce blob S3 ? » en déposant un fichier sous une clé aléatoire
unique qui s'auto-supprime à la sortie du bloc ; (c) les surfaces
multiples (CLI argparse + CLI click + HTTP FastAPI) sont
partagées avec le reste de la famille AI-Helpers — mêmes signatures,
aucune dérive.

Deux lignes sont notées `n/a` sur certains critères dans les notes
brutes et sont donc omises de la grille « en un coup d'œil » : le frère
`sftp-helper` parle SFTP, et non S3, de sorte que ses cellules
multi-fournisseur et constructeur d'URL ne s'appliquent pas.

## Quand choisir quoi

- **`bucket-helper`** — CRUD rapide en mode chemin sur S3 ou tout
  endpoint compatible S3 dans un service Python ; flux de stage-and-share
  où le nettoyage distant automatique compte ; quand on utilise déjà
  `os-helper` / `sftp-helper` et qu'on veut la même forme pour le
  stockage objet.
- **`boto3` / `botocore`** — on a besoin d'une fonctionnalité de SDK bas
  niveau que nous n'enveloppons pas (URL présignées, chiffrement côté
  serveur, copie multipart, SelectObjectContent, …) ; `botocore` quand
  on veut la couche de transport nue sous `boto3`.
- **`s3fs` / `fsspec`** — on veut un système de fichiers natif `fsspec`
  pour que `pandas` / `dask` / `polars` lisent directement depuis
  `s3://…`.
- **`awscli` / `gsutil`** — travail DevOps / sysadmin depuis le shell :
  synchronisations en masse, copies scriptées, sauvegardes pilotées par
  cron. Meilleure ergonomie que n'importe quelle bibliothèque Python
  pour cette tâche précise.
- **`minio` / `cloudpathlib` / `apache-libcloud`** — un seul usage
  étroit : le SDK MinIO du fournisseur, des chemins cloud façon
  `pathlib.Path`, ou une abstraction multi-cloud large qui dépasse
  largement S3.
- **`smart_open`** — on a seulement besoin de `open("s3://…")` et rien
  d'autre.
