# Nico Boats

Digest quotidien de bateaux d’occasion en Suisse (jusqu’à CHF 30’000, ou gratuits), pensé pour une place d’amarrage au Léman, à Genève.

La machine qui prépare le digest **ne peut pas** joindre un serveur SMTP. Les runners GitHub Actions le peuvent : le HTML est déposé ici, puis un workflow l’envoie via Infomaniak. Les mêmes données sont publiées en tableau vivant : **https://gael7777.github.io/nico-boats/**

## Filtre global

Les règles de sélection sont enregistrées et versionnées dans [`config/filtre_global.json`](config/filtre_global.json) (version 2, 15 novembre 2026). Le site les applique **par défaut** (bouton « Filtre global ON/OFF » pour tout afficher). Le digest quotidien et la sélection initiale s’appuient sur le même fichier.

| Critère | Règle |
| --- | --- |
| Type | Hors-bord à coque rigide uniquement. Pas de voiliers, annexes, pédalos ni bateaux à rames. **Pas de pneumatiques, gonflables ni semi-rigides (RIB)** depuis la version 2 : détection par catégorie du site, matériau (Hypalon / PVC), titre et type, description (sauf mention d’une annexe fournie avec un bateau rigide) et marques spécialisées (Zodiac, Bombard, Brig, Highfield, 3D Tender, Joker Boat, Lomac, BSC, Valiant, Grand…). Les marques mixtes (Ranieri, Capelli, Selva, Quicksilver…) ne sont exclues que pour leurs gammes pneumatiques. |
| Puissance | 40 à 90 CV |
| Largeur max. | 2,30 m |
| Longueur max. | 7,00 m |
| Prix max. | CHF 15’000 |
| Zone 1 (prioritaire) | Bateaux situés sur ou près des lacs Léman, de Neuchâtel, de Morat et de Bienne (communes, codes postaux, et distance à la rive si les coordonnées sont connues, rayon 12 km). |
| Zone 2 | Reste de la Suisse, présentée à part. Mention « Très bonne opportunité » si le prix est nettement sous des bateaux comparables (longueur / puissance / année), s’il y a une remorque, un moteur récent, etc. On reste ouvert au plus loin si ça vaut le déplacement. |

**Valeurs manquantes (N/A).** Si la puissance, la largeur ou la longueur n’est pas indiquée, le bateau **n’est pas écarté automatiquement**. Il reste visible dans le seau « À vérifier », pour autant que les autres critères correspondent et qu’il ne soit pas clairement hors sujet (« sans permis », épave à donner, moteur in-bord, etc.).

Le dépôt conserve **toutes** les annonces dans `data/listings.json`. Le filtre ne fait que choisir la vue par défaut et le contenu du digest.

## Déroulement d’une matinée

1. `python3 report/build.py` parcourt les sites, fusionne dans le magasin, écrit le digest du jour (uniquement les **nouveaux** bateaux qui passent le filtre), met à jour les données du site et, au besoin, les aperçus PNG.
2. [`publish_and_send.sh`](publish_and_send.sh) copie le HTML vers `digest/latest.html` et `digest/YYYY-MM-DD.html`, commite aussi `data/`, `site/data/`, `config/` et `report/digest/`, pousse `main` avec [`scripts/git_push.sh`](scripts/git_push.sh) (jeton seulement dans l’URL du push, jamais enregistré ni affiché), puis déclenche le workflow d’envoi (sauf avec `--no-send`).
3. [`.github/workflows/send-digest.yml`](.github/workflows/send-digest.yml) envoie le message via SMTP STARTTLS (Infomaniak).

Il n’y a **pas de cron** sur l’envoi. Rien ne part sans le script (ou un déclenchement manuel). Un push sur `site/`, `data/` ou `config/` redéploie le site Pages.

## Commandes du quotidien

Depuis `/workspace/projects/nico-boats`, avec `GITHUB_NICO_BOATS_TOKEN` dans l’environnement :

```bash
# 1. Collecte, fusion, digest filtré du jour, données du site
python3 report/build.py

# Recalcul sans retourner sur les sites (à partir du dernier scrape) :
# python3 report/build.py --no-collect

# 2. Commit (digest + data/ + site/data/ + config/), push, et envoi (destinataires = secret MAIL_RECIPIENTS)
#    Sujet par défaut : « Nico Boats – 24 novembre 2026 » (date en français, sans dépendre de la locale)
./publish_and_send.sh

# Pousser les données et le site sans envoyer d’e-mail :
# ./publish_and_send.sh --no-send
```

Aperçu sans push ni envoi :

```bash
./publish_and_send.sh --dry-run
```

**Attention au marquage.** Sans `--no-mark`, `build.py` marque immédiatement comme envoyés (`sent_in_digest = date du jour`) tous les bateaux du digest qu’il écrit. Toute reconstruction qui ne sera **pas** envoyée (test, correctif, ajout de sources) doit donc tourner avec `--no-mark`, sinon le digest suivant sauterait ces bateaux.

Options utiles : `--no-mark` (ne pas marquer les bateaux comme envoyés), `--no-shots` (pas d’aperçus PNG), `--no-enrich` (ne pas retravailler les fiches incomplètes), `--selection-initiale` (produire la sélection complète du jour, à ne pas envoyer).

### Déduplication

Le digest quotidien ne contient que les bateaux **actifs** qui passent le filtre et dont `sent_in_digest` vaut encore `N/A` (jamais envoyés). La première édition non filtrée du **15 novembre 2026** (912 bateaux, e-mail de test) sert de base : ces bateaux restent marqués `2026-11-15` et ne reparaissent pas dans un digest quotidien, même le jour même. Un relancement le jour J d’un digest déjà filtré reste possible (les bateaux marqués aujourd’hui, hors cette date de base, sont repris). Les baisses de prix d’un bateau déjà envoyé apparaissent dans une encadré « changements de prix » lorsqu’il y en a.

Une **sélection initiale** unique, en français, de *tous* les bateaux actuellement en ligne qui passent le filtre (indépendamment du marquage) se trouve dans `report/digest/selection-initiale-2026-11-15.html`. Elle n’est pas envoyée automatiquement : à relire avant tout envoi éventuel.

## Destinataires et SMTP

Le dépôt est public : les adresses des destinataires **ne figurent dans aucun fichier**.

| Élément | Valeur |
| --- | --- |
| Destinataires | secret Actions **`MAIL_RECIPIENTS`** (liste séparée par des virgules) |
| Expéditeur / utilisateur SMTP | `info@gmc-works.com` |
| Serveur | `mail.infomaniak.com:587` (STARTTLS, EHLO `gmc-works.com`) |
| Mot de passe | secret Actions **`SMTP_PASSWORD`** |

On peut remplacer les destinataires pour un envoi ponctuel avec l’entrée `recipients` du workflow. La laisser vide utilise le secret. Le jeton `GITHUB_NICO_BOATS_TOKEN` a besoin des droits **Contents**, **Actions** et **Workflows** ; ne jamais le commiter ni l’afficher.

Gmail coupe le HTML au-delà d’environ 102 Ko. Les gros jours restent donc sous ~95 Ko (résumé, meilleurs choix, bouton vers le tableau vivant). Les jours calmes listent tous les nouveaux bateaux.

## Magasin et site

| Chemin | Rôle |
| --- | --- |
| `config/filtre_global.json` | Filtre global versionné (source de vérité des règles) |
| `data/listings.json` | **Magasin maître** — une fiche par bateau (toutes les annonces) |
| `data/listings.csv` | Export plat, réécrit à chaque run |
| `site/` | Application statique GitHub Pages (tableau, fiches, carte), en français |
| `site/data/listings.json` | Copie du magasin **plus** les champs `_filtre` (zone, seau, opportunité) |
| `report/digest/latest.html` | Corps de l’e-mail du jour |

Sources (23.11.2026) : boat24 (bateau24.ch = boot24.ch), lakeboat.ch, petitesannonces.ch, aquaboat.ch. Bloqués : tutti.ch et anibis.ch depuis le 21.11.2026 (captcha Cloudflare Turnstile, aussi depuis GitHub Actions), ricardo.ch (captcha Cloudflare), Facebook Marketplace (connexion), swissboat.ch (mur anti-robot). Un même bateau publié sur plusieurs sites n’apparaît qu’une fois, avec les liens « aussi sur ». Le détail des sources, du classement et du schéma est dans [`report/README.md`](report/README.md).
