"""
Commandes de cocons sémantiques.

Usage:
    cw cocon identify [--output json|txt|csv]
    cw cocon detect-cannibalization <url>
    cw cocon validate <url>
"""

import click
import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

from scripts.sheets import SheetsClient
from scripts.cocon import CannibalizationDetector, SiblingFetcher
from scripts.wordpress.stseo_client import STSEOClient


@click.group()
def cocon():
    """Gestion des cocons sémantiques PARENT-CHILD."""
    pass


@cocon.command()
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@click.option('--output', type=click.Choice(['json', 'txt', 'csv', 'all']), default='all',
              help='Format de sortie (défaut: all)')
def identify(spreadsheet_id, output):
    """
    Identifie les relations PARENT-CHILD.

    Règle: H1 du CHILD = H2 du PARENT
    Migre identify_cocons.py
    """
    click.echo(f"\n🔍 IDENTIFICATION COCONS SÉMANTIQUES")
    click.echo(f"Spreadsheet: {spreadsheet_id}\n")

    # Charger le fichier JSON avec les structures
    outputs_dir = Path("outputs")
    json_files = sorted(outputs_dir.glob("articles_structure_*.json"))

    if not json_files:
        click.echo("❌ Aucun fichier de structure trouvé dans outputs/", err=True)
        click.echo("Lancez d'abord l'extraction des structures avec:", err=True)
        click.echo("  cw debug extract-structures --spreadsheet-id <ID>", err=True)
        raise click.Abort()

    latest_json = json_files[-1]
    click.echo(f"[1/4] Chargement structures: {latest_json.name}")

    with open(latest_json, 'r', encoding='utf-8') as f:
        articles_data = json.load(f)

    # Lire le spreadsheet pour obtenir les types de posts
    click.echo("[2/4] Lecture types de posts (PARENT/CHILD/STANDALONE)...")
    client = SheetsClient(spreadsheet_id=spreadsheet_id)
    sheet_data = client._read_sheet('Refreshs_Audit')

    # Créer un mapping row -> post_type
    post_types = {}
    for i, row in enumerate(sheet_data[1:], start=2):
        if len(row) > 5:
            post_type = row[5] if row[5] else 'STANDALONE'
            post_types[i] = post_type

    click.echo(f"  ✓ Types de posts chargés: {len(post_types)}")

    # Enrichir articles_data avec les types
    for article in articles_data:
        row = article['row']
        article['post_type'] = post_types.get(row, 'STANDALONE')

    # Séparer PARENT et CHILD
    parents = [a for a in articles_data if a['post_type'] == 'PARENT']
    children = [a for a in articles_data if a['post_type'] == 'CHILD']
    standalone = [a for a in articles_data if a['post_type'] == 'STANDALONE']

    click.echo(f"\n  Répartition:")
    click.echo(f"    PARENT:     {len(parents)}")
    click.echo(f"    CHILD:      {len(children)}")
    click.echo(f"    STANDALONE: {len(standalone)}")

    # Fonction de similarité
    def similarity(a, b):
        """Calcule la similarité entre deux textes (0-1)."""
        a_norm = a.lower().strip()
        b_norm = b.lower().strip()
        return SequenceMatcher(None, a_norm, b_norm).ratio()

    # Fonction pour trouver le parent d'un child
    def find_parent(child, parents, threshold=0.8):
        """Trouve le PARENT d'un CHILD en comparant le H1 du child avec les H2s des parents."""
        child_title = child['title']
        best_match = None
        best_score = 0
        best_h2 = None

        for parent in parents:
            for h2 in parent['h2s']:
                score = similarity(child_title, h2)
                if score > best_score:
                    best_score = score
                    best_match = parent
                    best_h2 = h2

        if best_score >= threshold:
            return best_match, best_h2, best_score
        return None, None, best_score

    # Identifier les cocons
    click.echo(f"\n[3/4] Identification des cocons...")
    click.echo(f"{'='*100}")

    cocon_mapping = []

    for child in children:
        parent, matching_h2, score = find_parent(child, parents, threshold=0.70)

        mapping_entry = {
            'child_row': child['row'],
            'child_url': child['url'],
            'child_title': child['title'],
            'child_blog': child['blog_id'],
            'parent_found': parent is not None,
            'parent_row': parent['row'] if parent else None,
            'parent_url': parent['url'] if parent else None,
            'parent_title': parent['title'] if parent else None,
            'parent_blog': parent['blog_id'] if parent else None,
            'matching_h2': matching_h2,
            'similarity_score': round(score, 2)
        }

        cocon_mapping.append(mapping_entry)

        if parent:
            click.echo(f"✓ CHILD (L{child['row']:3d}): {child['title'][:60]}")
            click.echo(f"  → PARENT (L{parent['row']:3d}): {parent['title'][:60]}")
            click.echo(f"  → H2: {matching_h2[:60]}")
            click.echo(f"  → Similarité: {score:.2%}\n")
        else:
            click.echo(f"✗ CHILD (L{child['row']:3d}): {child['title'][:60]}")
            click.echo(f"  → AUCUN PARENT (meilleur score: {score:.2%})\n")

    # Statistiques
    found_count = sum(1 for m in cocon_mapping if m['parent_found'])
    click.echo(f"{'='*100}")
    click.echo(f"\n📊 STATISTIQUES:")
    click.echo(f"  Total CHILD:        {len(children)}")
    click.echo(f"  PARENT trouvés:     {found_count}")
    click.echo(f"  PARENT non trouvés: {len(children) - found_count}")
    click.echo(f"  Taux de matching:   {found_count/len(children)*100:.1f}%\n")

    # Sauvegarder les résultats
    click.echo(f"[4/4] Sauvegarde résultats...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if output in ['json', 'all']:
        json_file = outputs_dir / f"cocon_mapping_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(cocon_mapping, f, ensure_ascii=False, indent=2)
        click.echo(f"  ✓ JSON: {json_file}")

    if output in ['txt', 'all']:
        txt_file = outputs_dir / f"cocon_mapping_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write('='*100 + '\n')
            f.write('MAPPING DES COCONS SÉMANTIQUES (PARENT-CHILD)\n')
            f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write('='*100 + '\n\n')

            f.write(f'Total CHILD: {len(children)}\n')
            f.write(f'PARENT trouvés: {found_count}\n')
            f.write(f'PARENT non trouvés: {len(children) - found_count}\n')
            f.write(f'Taux de matching: {found_count/len(children)*100:.1f}%\n\n')
            f.write('='*100 + '\n\n')

            # Grouper par parent
            parent_groups = {}
            for mapping in cocon_mapping:
                if mapping['parent_found']:
                    parent_url = mapping['parent_url']
                    if parent_url not in parent_groups:
                        parent_groups[parent_url] = {
                            'parent_row': mapping['parent_row'],
                            'parent_title': mapping['parent_title'],
                            'parent_blog': mapping['parent_blog'],
                            'children': []
                        }
                    parent_groups[parent_url]['children'].append(mapping)

            # Afficher par cocon
            for parent_url, group in parent_groups.items():
                f.write(f"\nCOCON: {group['parent_title']}\n")
                f.write(f"Parent (Ligne {group['parent_row']}): {parent_url}\n")
                f.write(f"Blog: {group['parent_blog']}\n")
                f.write(f"Nombre d'enfants: {len(group['children'])}\n")
                f.write('-'*100 + '\n')

                for idx, child in enumerate(group['children'], 1):
                    f.write(f"\n  {idx}. CHILD (Ligne {child['child_row']})\n")
                    f.write(f"     Titre: {child['child_title']}\n")
                    f.write(f"     URL: {child['child_url']}\n")
                    f.write(f"     H2 parent: {child['matching_h2']}\n")
                    f.write(f"     Similarité: {child['similarity_score']:.2%}\n")

                f.write('\n' + '='*100 + '\n')

            # Orphelins
            orphans = [m for m in cocon_mapping if not m['parent_found']]
            if orphans:
                f.write(f"\n\nARTICLES CHILD ORPHELINS:\n")
                f.write('='*100 + '\n')
                for orphan in orphans:
                    f.write(f"\nLigne {orphan['child_row']}: {orphan['child_title']}\n")
                    f.write(f"URL: {orphan['child_url']}\n")
                    f.write(f"Meilleur score: {orphan['similarity_score']:.2%}\n")

        click.echo(f"  ✓ TXT: {txt_file}")

    if output in ['csv', 'all']:
        csv_file = outputs_dir / f"cocon_mapping_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write('Child Row,Child Blog,Child URL,Child Title,Parent Found,Parent Row,Parent Blog,Parent URL,Parent Title,Matching H2,Similarity Score\n')
            for m in cocon_mapping:
                f.write(f"{m['child_row']},")
                f.write(f'"{m["child_blog"]}",')
                f.write(f'"{m["child_url"]}",')
                f.write(f'"{m["child_title"]}",')
                f.write(f"{'YES' if m['parent_found'] else 'NO'},")
                f.write(f"{m['parent_row'] if m['parent_row'] else ''},")
                f.write(f'"{m["parent_blog"] if m["parent_blog"] else ""}",')
                f.write(f'"{m["parent_url"] if m["parent_url"] else ""}",')
                f.write(f'"{m["parent_title"] if m["parent_title"] else ""}",')
                f.write(f'"{m["matching_h2"] if m["matching_h2"] else ""}",')
                f.write(f"{m['similarity_score']}\n")

        click.echo(f"  ✓ CSV: {csv_file}")

    click.echo(f"\n✅ Done!")


@cocon.command()
@click.argument('url')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def detect_cannibalization(url, spreadsheet_id):
    """
    Détecte la cannibalization pour une URL.

    Alias de: cw audit cannibalization <url>
    """
    from .audit import audit
    ctx = click.Context(audit)
    ctx.invoke(audit.commands['cannibalization'], url=url, blog=None, spreadsheet_id=spreadsheet_id)


@cocon.command()
@click.argument('url')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def validate(url, spreadsheet_id):
    """
    Valide les liens PARENT-CHILD pour une URL.

    Vérifie que les liens internes sont corrects.
    """
    click.echo(f"\n🔍 VALIDATION COCON")
    click.echo(f"URL: {url}\n")

    # Fetch content via STSEO API
    click.echo("[1/2] Récupération contenu via STSEO API...")
    stseo = STSEOClient()
    stseo_result = stseo.get_post_content_by_link(url)

    if not stseo_result or not stseo_result.get("post_content"):
        click.echo("  ✗ Impossible de récupérer le contenu via STSEO", err=True)
        raise click.Abort()

    html = stseo_result["post_content"]
    click.echo(f"  ✓ HTML récupéré ({len(html)} chars)")

    # Fetch siblings
    click.echo("[2/2] Validation liens...")
    sheets_client = SheetsClient(spreadsheet_id)
    fetcher = SiblingFetcher(sheets_client)
    siblings = fetcher.fetch_siblings(url)

    if not siblings:
        click.echo("  ℹ Article STANDALONE (pas de cocon)")
        return

    # Extraire les liens internes de l'HTML
    import re
    internal_links = re.findall(r'href="(https?://[^"]+)"', html)

    sibling_urls = [s.url for s in siblings]
    found_links = [link for link in internal_links if link in sibling_urls]

    click.echo(f"\n📊 RÉSULTATS:")
    click.echo(f"  Siblings attendus:  {len(siblings)}")
    click.echo(f"  Liens trouvés:      {len(found_links)}")

    if len(found_links) == len(siblings):
        click.echo(f"\n✅ Tous les liens PARENT-CHILD sont présents")
    else:
        click.echo(f"\n⚠ Liens manquants: {len(siblings) - len(found_links)}")
        missing = set(sibling_urls) - set(found_links)
        for link in missing:
            click.echo(f"    - {link}")
