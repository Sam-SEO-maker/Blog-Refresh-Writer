# 🔍 Diagnostic Google Sheets - Content Writer

## ✅ Ce qui fonctionne

1. **Service Account** : ✅ Configuré et fonctionnel
   - Email: `sam-workspace@sam-workspace-tools.iam.gserviceaccount.com`
   - Fichier: `C:\Users\samue\.credentials\google\google-service-account.json`

2. **Connexion API** : ✅ L'API Google Sheets est accessible

3. **Permissions** : ✅ Le service account a les droits **Éditeur**
   - Lecture: ✅ Fonctionne
   - Écriture: ✅ Fonctionne

4. **Configuration** : ✅ Spreadsheet ID correct
   - ID: `1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M`
   - Nom: "Refresh SEO Audit v2.0"
   - Fichier config: `_shared/config/sheets_config.json`

5. **Méthode `_update_cell`** : ✅ Fonctionne parfaitement

## ❌ Ce qui ne fonctionne PAS

### Problème identifié : `update_audit_gsc()` échoue avec métriques

**Symptômes** :
- ✅ `update_audit_gsc(url, status)` : FONCTIONNE
- ❌ `update_audit_gsc(url, status, metrics={...})` : ÉCHOUE (retourne `False`)

**Test effectué** :
```python
# ✅ RÉUSSIT
client.update_audit_gsc(
    url="https://cours-particuliers.com/...",
    status="✅ Test OK"
)

# ❌ ÉCHOUE
client.update_audit_gsc(
    url="https://cours-particuliers.com/...",
    status="✅ Test avec métriques",
    metrics={
        "impressions_30d": 999,
        "clicks_30d": 42,
        "ctr_30d": 4.2
    }
)
```

**Résultat** :
- Le `status` est écrit dans la colonne H ✅
- Les `metrics` NE SONT PAS écrites dans J, K, L ❌

## 🔍 Cause probable

Le problème se situe dans [`scripts/sheets/sheets_client.py`](scripts/sheets/sheets_client.py#L1060-L1063) :

```python
# Lignes 1060-1063
if metrics:
    self._update_cell(self.SHEET_REFRESHS_AUDIT, f"J{i}", metrics.get("impressions_30d", 0))
    self._update_cell(self.SHEET_REFRESHS_AUDIT, f"K{i}", metrics.get("clicks_30d", 0))
    self._update_cell(self.SHEET_REFRESHS_AUDIT, f"L{i}", metrics.get("ctr_30d", 0.0))
```

**Hypothèses** :
1. Une des méthodes `_update_cell` pour J, K ou L lève une exception
2. Le bloc `try/except` capture l'erreur sans la logger (ligne 1071-1072)
3. La méthode retourne `False` silencieusement

**Problème du code actuel** :
```python
except Exception:  # ❌ Capture TOUTES les exceptions sans les afficher
    return False
```

## ✅ Solutions

### Solution 1 : Améliorer le logging des erreurs (RECOMMANDÉ)

Modifier [`scripts/sheets/sheets_client.py`](scripts/sheets/sheets_client.py#L1071-L1072) :

```python
# AVANT (ligne 1071-1072)
except Exception:
    return False

# APRÈS
except Exception as e:
    logger.error(f"update_audit_gsc error for URL {url}: {e}")
    import traceback
    traceback.print_exc()
    return False
```

**Faire pareil pour** :
- `update_audit_serp()` (ligne ~1109)
- `update_decision()` (ligne ~1147)
- `update_refresh_status()` (ligne ~1176)

### Solution 2 : Vérifier la longueur des lignes

Ajouter des vérifications avant d'accéder aux indices :

```python
if metrics:
    if len(row) > 9:  # Vérifier que la colonne J existe
        self._update_cell(self.SHEET_REFRESHS_AUDIT, f"J{i}", metrics.get("impressions_30d", 0))
    if len(row) > 10:  # Colonne K
        self._update_cell(self.SHEET_REFRESHS_AUDIT, f"K{i}", metrics.get("clicks_30d", 0))
    if len(row) > 11:  # Colonne L
        self._update_cell(self.SHEET_REFRESHS_AUDIT, f"L{i}", metrics.get("ctr_30d", 0.0))
```

### Solution 3 : Étendre les lignes vides

Si certaines lignes n'ont pas toutes les colonnes, les étendre avant update :

```python
# Avant les updates, s'assurer que la ligne a au moins 28 colonnes
while len(row) < 28:
    row.append("")
```

## 🧪 Scripts de test créés

1. **`test_sheets_connection.py`** : Test de connexion basique
2. **`test_sheets_from_config.py`** : Test avec la config du projet
3. **`test_sheets_write.py`** : Test d'écriture simple
4. **`test_workflow_updates.py`** : Test des méthodes d'update
5. **`test_workflow_updates_debug.py`** : Test avec logs verbeux
6. **`test_refresh_audit_row.py`** : Test de RefreshAuditRow.from_list()
7. **`test_direct_update.py`** : Test direct avec monkey-patch ⭐

**Script recommandé pour débugger** : `test_direct_update.py`

## 📝 Recommandations

1. **Immédiat** : Appliquer la **Solution 1** (améliorer logging)
2. **Court terme** : Vérifier pourquoi les lignes n'ont pas toutes 28 colonnes
3. **Moyen terme** : Ajouter des tests unitaires pour les méthodes d'update
4. **Long terme** : Considérer un système de validation de structure de données

## 🔗 Liens utiles

- Spreadsheet: https://docs.google.com/spreadsheets/d/1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M
- Config: [`_shared/config/sheets_config.json`](_shared/config/sheets_config.json)
- SheetsClient: [`scripts/sheets/sheets_client.py`](scripts/sheets/sheets_client.py)

---

**Diagnostic créé le** : 2026-02-13
**Statut** : Problème identifié, solutions proposées
