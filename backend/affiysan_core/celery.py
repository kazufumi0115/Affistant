import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "affiysan_core.settings")

app = Celery("affiysan_core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
