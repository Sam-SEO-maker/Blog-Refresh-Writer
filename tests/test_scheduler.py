"""
Tests pour le module scheduler.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.agent.scheduler import TaskScheduler, TaskPriority, ScheduledTask


class TestTaskScheduler:
    """Tests pour TaskScheduler."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.scheduler = TaskScheduler()

    def test_add_task(self):
        """Test ajout d'une tâche."""
        self.scheduler.add_task(
            url="https://example.com/article",
            blog_id="enseigna",
            action="AUDIT",
            priority=TaskPriority.MEDIUM,
        )

        assert self.scheduler.size() == 1
        assert not self.scheduler.is_empty()

    def test_priority_ordering(self):
        """Test ordre par priorité."""
        # Ajouter dans l'ordre inverse
        self.scheduler.add_task(
            url="https://example.com/low",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.LOW,
        )
        self.scheduler.add_task(
            url="https://example.com/critical",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.CRITICAL,
        )
        self.scheduler.add_task(
            url="https://example.com/medium",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.MEDIUM,
        )

        # La tâche critique doit sortir en premier
        task = self.scheduler.get_next()
        assert task.url == "https://example.com/critical"
        assert task.priority == TaskPriority.CRITICAL.value

        # Puis medium
        task = self.scheduler.get_next()
        assert task.url == "https://example.com/medium"

        # Puis low
        task = self.scheduler.get_next()
        assert task.url == "https://example.com/low"

    def test_no_duplicates(self):
        """Test pas de doublons."""
        url = "https://example.com/unique"

        self.scheduler.add_task(url=url, blog_id="test", action="AUDIT")
        self.scheduler.add_task(url=url, blog_id="test", action="AUDIT")  # Doublon

        assert self.scheduler.size() == 1

    def test_get_next_empty(self):
        """Test get_next sur file vide."""
        task = self.scheduler.get_next()
        assert task is None

    def test_peek(self):
        """Test peek sans retirer."""
        self.scheduler.add_task(
            url="https://example.com/article",
            blog_id="test",
            action="AUDIT",
        )

        # Peek ne retire pas
        task1 = self.scheduler.peek()
        task2 = self.scheduler.peek()

        assert task1 is not None
        assert task1.url == task2.url
        assert self.scheduler.size() == 1

    def test_get_batch(self):
        """Test récupération batch."""
        for i in range(5):
            self.scheduler.add_task(
                url=f"https://example.com/article-{i}",
                blog_id="test",
                action="AUDIT",
            )

        batch = self.scheduler.get_batch(size=3)

        assert len(batch) == 3
        assert self.scheduler.size() == 2

    def test_get_batch_partial(self):
        """Test batch plus grand que la file."""
        self.scheduler.add_task(
            url="https://example.com/only",
            blog_id="test",
            action="AUDIT",
        )

        batch = self.scheduler.get_batch(size=10)

        assert len(batch) == 1
        assert self.scheduler.is_empty()

    def test_add_batch(self):
        """Test ajout batch."""
        tasks = [
            {"url": "https://example.com/1", "blog_id": "test", "action": "AUDIT"},
            {"url": "https://example.com/2", "blog_id": "test", "priority": 1},
            {"url": "https://example.com/3", "blog_id": "test"},
        ]

        self.scheduler.add_batch(tasks)

        assert self.scheduler.size() == 3

    def test_clear(self):
        """Test vidage de la file."""
        for i in range(3):
            self.scheduler.add_task(
                url=f"https://example.com/{i}",
                blog_id="test",
                action="AUDIT",
            )

        self.scheduler.clear()

        assert self.scheduler.is_empty()
        assert self.scheduler.size() == 0

    def test_metadata(self):
        """Test métadonnées sur les tâches."""
        self.scheduler.add_task(
            url="https://example.com/article",
            blog_id="test",
            action="AUDIT",
            metadata={"source": "manual", "priority_reason": "urgent"},
        )

        task = self.scheduler.get_next()

        assert task.metadata["source"] == "manual"
        assert task.metadata["priority_reason"] == "urgent"


class TestRateLimiting:
    """Tests pour le rate limiting."""

    def setup_method(self):
        self.scheduler = TaskScheduler()

    def test_can_call_api_initially(self):
        """Test appel possible initialement."""
        assert self.scheduler.can_call_api("gsc") is True
        assert self.scheduler.can_call_api("dataforseo") is True
        assert self.scheduler.can_call_api("sheets") is True

    def test_can_call_unknown_api(self):
        """Test API inconnue toujours autorisée."""
        assert self.scheduler.can_call_api("unknown_api") is True

    def test_rate_limit_reached(self):
        """Test limite atteinte."""
        # GSC limite = 60/minute
        for _ in range(60):
            self.scheduler.record_api_call("gsc")

        assert self.scheduler.can_call_api("gsc") is False

    def test_rate_limit_recovery(self):
        """Test récupération après délai."""
        # Simuler des appels anciens
        old_time = datetime.now() - timedelta(seconds=61)
        self.scheduler._api_calls["gsc"] = [old_time] * 60

        # Devrait être autorisé car appels > 1 minute
        assert self.scheduler.can_call_api("gsc") is True

    def test_get_wait_time_zero(self):
        """Test temps d'attente nul si possible."""
        wait = self.scheduler.get_wait_time("gsc")
        assert wait == 0.0

    def test_get_wait_time_positive(self):
        """Test temps d'attente positif si limité."""
        # Remplir la limite
        for _ in range(60):
            self.scheduler.record_api_call("gsc")

        wait = self.scheduler.get_wait_time("gsc")

        assert wait > 0
        assert wait <= 60  # Max 60 secondes

    def test_record_api_call(self):
        """Test enregistrement appel."""
        initial_count = len(self.scheduler._api_calls["gsc"])

        self.scheduler.record_api_call("gsc")

        assert len(self.scheduler._api_calls["gsc"]) == initial_count + 1


class TestSchedulerStats:
    """Tests pour les statistiques."""

    def setup_method(self):
        self.scheduler = TaskScheduler()

    def test_get_stats_empty(self):
        """Test stats file vide."""
        stats = self.scheduler.get_stats()

        assert stats["queue_size"] == 0
        assert stats["processed_count"] == 0
        assert stats["by_priority"] == {}

    def test_get_stats_with_tasks(self):
        """Test stats avec tâches."""
        self.scheduler.add_task(
            url="https://example.com/critical",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.CRITICAL,
        )
        self.scheduler.add_task(
            url="https://example.com/medium1",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.MEDIUM,
        )
        self.scheduler.add_task(
            url="https://example.com/medium2",
            blog_id="test",
            action="AUDIT",
            priority=TaskPriority.MEDIUM,
        )

        stats = self.scheduler.get_stats()

        assert stats["queue_size"] == 3
        assert stats["by_priority"]["CRITICAL"] == 1
        assert stats["by_priority"]["MEDIUM"] == 2

    def test_get_stats_processed(self):
        """Test compteur processed."""
        self.scheduler.add_task(
            url="https://example.com/1",
            blog_id="test",
            action="AUDIT",
        )
        self.scheduler.add_task(
            url="https://example.com/2",
            blog_id="test",
            action="AUDIT",
        )

        # Traiter une tâche
        self.scheduler.get_next()

        stats = self.scheduler.get_stats()

        assert stats["queue_size"] == 1
        assert stats["processed_count"] == 1

    def test_queue_preview(self):
        """Test aperçu de la file."""
        for i in range(5):
            self.scheduler.add_task(
                url=f"https://example.com/{i}",
                blog_id="test",
                action="AUDIT",
                priority=TaskPriority.MEDIUM,
            )

        preview = self.scheduler.get_queue_preview(limit=3)

        assert len(preview) == 3
        assert all("url" in p for p in preview)
        assert all("priority" in p for p in preview)

        # La file ne doit pas être modifiée
        assert self.scheduler.size() == 5
