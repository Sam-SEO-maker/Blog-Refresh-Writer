"""
Fixtures pytest partagées pour les tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def base_path():
    """Chemin racine du projet."""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_html():
    """HTML d'exemple pour les tests."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Comment apprendre les maths efficacement - Guide 2024</title>
    <meta name="description" content="Découvrez nos conseils pour apprendre les maths.">
</head>
<body>
    <h1>Comment apprendre les maths efficacement</h1>

    <p>Introduction avec <a href="/cours-maths">lien interne</a>.</p>

    <img src="/images/math-formulas.jpg" alt="Formules mathématiques">

    <h2>Les bases fondamentales</h2>
    <p>Le premier point important est de maîtriser les bases.</p>
    <p>Selon une étude de 2023, 80% des étudiants progressent plus vite.</p>

    <img src="/images/student-studying.png" alt="Étudiant qui étudie">

    <h2>Méthodes d'apprentissage</h2>
    <p>Il existe plusieurs méthodes efficaces:</p>
    <ul>
        <li>Pratique régulière</li>
        <li>Exercices variés</li>
        <li>Révisions espacées</li>
    </ul>

    <p>Pour un accompagnement personnalisé, consultez
    <a href="https://www.superprof.fr/cours/maths">Superprof</a>.</p>

    <h2>Ressources recommandées</h2>
    <p>Voici quelques <a href="/ressources-maths">ressources utiles</a>.</p>
    <p>Voir aussi <a href="https://eduscol.education.fr">Eduscol</a>.</p>

    <h2>FAQ</h2>
    <h3>Combien de temps pour progresser ?</h3>
    <p>En général, 3 à 6 mois de pratique régulière.</p>
</body>
</html>
"""


@pytest.fixture
def sample_html_no_superprof():
    """HTML sans lien Superprof."""
    return """
<!DOCTYPE html>
<html>
<body>
    <h1>Article sans Superprof</h1>
    <p>Contenu sans lien Superprof.</p>
    <img src="/image.jpg" alt="Image">
    <a href="/interne">Lien interne</a>
</body>
</html>
"""


@pytest.fixture
def sample_html_blacklisted():
    """HTML avec liens blacklistés."""
    return """
<!DOCTYPE html>
<html>
<body>
    <h1>Article avec liens blacklistés</h1>
    <p>Voir aussi <a href="https://acadomia.fr">Acadomia</a>.</p>
    <p>Et <a href="https://kelprof.com">Kelprof</a>.</p>
    <a href="https://www.superprof.fr">Superprof</a>
</body>
</html>
"""


@pytest.fixture
def sample_audit_data():
    """Données d'audit d'exemple."""
    return {
        "url": "https://example.com/article",
        "overall_score": 65,
        "performance": {
            "impressions_30d": 1000,
            "clicks_30d": 15,
            "ctr_30d": 0.015,
            "avg_position": 12.5,
            "main_keyword": "apprendre maths",
            "keyword_trend": -0.15,
        },
        "content": {
            "word_count": 1200,
            "h1_count": 1,
            "h2_count": 4,
            "images_count": 2,
            "internal_links_count": 3,
            "external_links_count": 2,
            "has_faq": True,
            "last_modified": "2023-06-15",
        },
        "cannibalization": {
            "has_cannibalization": False,
            "severity": "none",
            "competing_urls": [],
        },
        "intent": {
            "has_intent_shift": False,
            "current_intent": "informational",
            "serp_intent": "informational",
        },
        "serp": {
            "dominant_format": "guide",
            "paa_questions": [
                "Comment progresser en maths ?",
                "Quelle méthode pour apprendre les maths ?",
            ],
        },
        "alerts": ["CTR faible (<2%)", "Contenu >12 mois"],
        "recommendations": [
            "Optimiser le titre pour améliorer le CTR",
            "Mettre à jour les statistiques (2023 → 2025)",
        ],
    }


@pytest.fixture
def sample_audit_data_cannibalization():
    """Données d'audit avec cannibalisation."""
    return {
        "url": "https://example.com/article-1",
        "overall_score": 45,
        "performance": {
            "impressions_30d": 500,
            "clicks_30d": 5,
            "ctr_30d": 0.01,
            "avg_position": 18.0,
            "main_keyword": "cours maths",
        },
        "cannibalization": {
            "has_cannibalization": True,
            "severity": "high",
            "overlap_score": 0.75,
            "competing_urls": [
                "https://example.com/article-2",
                "https://example.com/article-3",
            ],
            "suggested_action": "REDIRECT_301",
            "redirect_target": "https://example.com/article-2",
        },
        "alerts": ["Cannibalisation sévère détectée"],
    }


@pytest.fixture
def sample_audit_data_intent_shift():
    """Données d'audit avec shift d'intention."""
    return {
        "url": "https://example.com/article",
        "overall_score": 55,
        "performance": {
            "main_keyword": "prix cours maths",
            "keyword_trend": -0.25,
            "variant_trends": {
                "tarif cours maths": 0.15,
                "combien coute cours maths": 0.20,
            },
        },
        "intent": {
            "has_intent_shift": True,
            "current_intent": "informational",
            "serp_intent": "transactional",
            "confidence": 0.85,
        },
        "alerts": ["Shift d'intention détecté (info → transactionnel)"],
    }


@pytest.fixture
def decision_rules():
    """Règles de décision de test."""
    return {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "low_ctr_high_impressions",
                "name": "CTR faible avec impressions élevées",
                "conditions": {
                    "ctr_30d": {"operator": "<", "value": 0.02},
                    "impressions_30d": {"operator": ">", "value": 500},
                },
                "action": "TITLE_OPTIMIZATION",
                "priority": 1,
            },
            {
                "rule_id": "severe_cannibalization",
                "name": "Cannibalisation sévère",
                "conditions": {
                    "cannibalization.severity": {"operator": "==", "value": "high"},
                },
                "action": "REDIRECT_301",
                "priority": 1,
            },
            {
                "rule_id": "content_stale",
                "name": "Contenu obsolète",
                "conditions": {
                    "content.age_months": {"operator": ">", "value": 12},
                },
                "action": "PARTIAL_REFRESH",
                "priority": 3,
            },
        ],
    }


@pytest.fixture
def blog_config_enseigna():
    """Configuration du blog Enseigna."""
    return {
        "blog_id": "enseigna",
        "domain": "enseigna.fr",
        "gsc_property": "https://enseigna.fr/",
        "content_type": "review_comparatif",
        "subject_category": "education_reviews",
        "superprof_anchor_style": "natural_varied",
        "min_word_count": 1500,
        "required_elements": ["rating_table", "verdict_box"],
        "prompt_overrides": {
            "intro_style": "Commencer par un verdict direct",
            "tone": "analytique et objectif",
        },
    }
