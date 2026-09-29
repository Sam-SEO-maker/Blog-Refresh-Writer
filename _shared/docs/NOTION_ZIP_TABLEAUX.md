# Joindre les ZIP de tableaux aux commandes Notion

Chaque ligne de refresh de la base Notion **« Resources - Main Database »**
(section « Ressources section » de la page *FR - Blog & Ressources Order*) doit
porter, dans le corps de sa page, le ZIP des CSV de tableaux de l'article —
`outputs/csv_zips/{slug}_tableaux.zip`.

Le geste manuel est : ouvrir la ligne depuis la colonne `Title (Main KW)`, taper
`/fichiers`, choisir le ZIP sur le disque. Ce document décrit comment l'automatiser.

## Ce qui n'est PAS possible

**`Title (Main KW)` ne peut pas recevoir le fichier.** C'est la propriété *titre*
de la base (`"type": "title"`), et une propriété titre n'accepte que du texte :
l'API rejette un payload `files` dessus. La base ne comporte d'ailleurs aucune
propriété de type `files`.

Le fichier vit donc **dans le corps de la page**, comme un bloc `file` — ce que
`/fichiers` produit. C'est un bloc, pas une valeur de propriété, et c'est cette
distinction qui décide de l'appel API à utiliser.

## Quel accès utiliser

| Chemin | Accès à la base | Verdict |
|---|---|---|
| Connecteur MCP Notion | **oui** | le seul qui marche aujourd'hui |
| `NOTION_TOKEN` du `.env` (REST) | **non — 404** | inutilisable en l'état |

La base source (`6dc43079-14bb-430b-bd32-4db038eb1086`) n'est pas partagée avec
l'intégration qui porte le `NOTION_TOKEN`. Tout le code Python (`orders_sync.py`,
donc `/sheets-update`) passe par ce token : il ne peut pas joindre de fichier, et
ne peut d'ailleurs plus rien lire de cette base.

> **Piège** : l'id affiché dans l'URL Notion (`1ebd6418-695a-80ff-…`) est celui
> d'une **base liée**, que l'API refuse explicitement
> (« Database retrievals do not support linked databases »). L'id à utiliser est
> celui de la base source, conservé dans `notion.orders.database_id`.

Pour rendre l'automatisation exécutable en Python, il faudrait repartager la base
source avec l'intégration. Tant que ce n'est pas fait, la procédure ci-dessous
est jouée par l'agent via le MCP.

## La procédure, en trois appels

1. **Créer l'upload** — `notion-create-file-upload` avec `filename`
   (`{slug}_tableaux.zip`). Retourne un `file_upload_id`, une `upload_url` et un
   `authorization` à usage unique, valables ~20 minutes.

2. **Envoyer le fichier** — un POST multipart, champ `file` :

   ```bash
   curl -s -X POST "<upload_url>" \
     -H "authorization: Bearer <token rendu à l'étape 1>" \
     -F "file=@{slug}_tableaux.zip;type=application/zip"
   ```

   La réponse doit porter `"status": "uploaded"`.

3. **Joindre à la page** — `notion-update-page` avec `command: "insert_content"`,
   `position: {"type": "end"}` et pour contenu :

   ```
   <file src="file-upload://<file_upload_id>"></file>
   ```

   Les paramètres sont passés **à la racine** de l'appel, pas dans une enveloppe
   `data`.

Le résultat est indiscernable d'un `/fichiers` manuel : la page porte un bloc
`<file src="attachment:…:{slug}_tableaux.zip">`.

Limite de taille : 20 Mio pour cet upload en une passe. Les ZIP de tableaux font
quelques centaines d'octets à quelques Kio, l'ordre de grandeur est sans objet.

## Apparier une ligne Notion et un ZIP

La clé est la colonne **`Local resource URL`** : son dernier segment, privé de
`.html`, est le slug, et le ZIP s'appelle `{slug}_tableaux.zip`.

`outputs/wp_backups/_publications.jsonl` donne le même pont pour les articles
publiés (`{"slug": …, "url": …}`), une ligne par publication réussie.

Deux pièges relevés en production :

- **Les ZIP ne sont pas tous à la racine de `csv_zips/`.** Ils existent aussi
  dans des sous-dossiers datés (`articles_260909/`) et dans `_archive/`. Ne
  chercher qu'à la racine sous-estime la couverture du simple au double.
  Certains noms archivés portent un préfixe de lot
  (`articles_260903__{slug}_tableaux.zip`) : le slug se lit après `__`.
- **Un même slug peut avoir plusieurs ZIP.** Vérifié sur 25 cas : les contenus
  (noms + CRC des CSV) étaient strictement identiques. Prendre celui de la racine
  en priorité, sinon n'importe lequel.

Quelques noms historiques gardent le `.html` du fichier source
(`divergence-plaques-tectoniques.html_tableaux.zip`,
`{slug}.html_refreshed_tableaux.zip`). Ce sont des vestiges : les ZIP produits
aujourd'hui suivent `{slug}_tableaux.zip`.

## Quand déclencher

**À la publication, pas à la commande.** Quand `/sheets-update` crée la ligne,
l'article n'est pas écrit et le ZIP n'existe pas encore. Le moment où
l'appariement est garanti est le push : `push_to_wp` écrit alors
`_publications.jsonl`, l'URL est connue et le ZIP vient d'être produit.

Un rattrapage rejouable reste utile pour le stock. Avant toute écriture en série,
lire l'état réel des pages : une page qui porte déjà son bloc `file` ne doit pas
en recevoir un second, et `insert_content` ne déduplique pas.

## Le câblage automatique

`scripts/notion/zip_attachment.py` fait les trois appels ci-dessus, et
`attach_tables_zip_message()` est appelé après chaque publication réussie, dans
`cli/commands/finalize.py` et `cli/commands/push.py` — juste après
`mark_published`, dont il reprend le contrat : **ne lève jamais**. L'article est
déjà en ligne à ce moment-là ; une base Notion injoignable ne doit pas
transformer une publication réussie en échec, elle affiche une ligne et c'est
tout.

Il ne se passe rien, silencieusement, dans deux cas légitimes : l'article n'a pas
de tableau (`no_zip`), ou le site ne déclare pas de base de commandes
(`no_config`, cas d'`enseigna.fr`). Tout le reste est signalé, sans quoi le
câblage pourrait mourir sans que personne ne le voie.

Les raisons rendues : `attached`, `already`, `no_token`, `no_access`, `no_row`,
`unreadable`, `upload_failed`, `block_failed`.

> `no_access` et `no_row` sont distingués à dessein. `query_database` avale le
> 404 et rend une liste vide : une base inaccessible ressemble alors à une base
> sans la ligne cherchée. Les confondre enverrait chercher une ligne manquante
> dans une base qu'on ne peut pas lire.

### État actuel : le partage manque

Le `NOTION_TOKEN` du `.env` **n'a pas accès** à la base de commandes (404 sur la
base comme sur une page précise, vérifié). Le câblage est donc en place et
inerte : il affiche `no_access` à chaque publication.

Pour l'activer, partager la base **source** avec l'intégration qui porte le
`NOTION_TOKEN` (⋯ → Connexions). Le même partage débloque `/sheets-update`, qui
tape sur la même base et est cassé pour la même raison.

En attendant, l'attachement se fait par le connecteur MCP Notion, qui a l'accès.

## Toujours relire après écriture

`insert_content` peut répondre `{"page_id": …}` et **poser le bloc deux fois**.
Observé sur 2 pages d'un lot de 15, pour un seul appel chacune : deux blocs
portant le même nom de fichier mais deux `attachment` distincts. L'accusé de
réception ne dit donc pas combien de blocs existent — seul un `notion-fetch`
après coup le dit.

Réparation : `notion-update-page` avec `command: "replace_content"` et, pour
`new_str`, le `<file src="…">` du bloc à conserver **recopié tel quel depuis le
fetch** (l'URL `file://…` encodée, pas un `file-upload://`, qui est à usage
unique et déjà consommé). Les autres blocs disparaissent, le fichier gardé reste
intact.
