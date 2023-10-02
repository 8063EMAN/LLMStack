import logging

from django.apps import AppConfig

from llmstack.apps.types.app_type_interface import AppTypeInterface
from llmstack.apps.types.agent import Agent
from llmstack.apps.types.chat import ChatApp
from llmstack.apps.types.web import WebApp

logger = logging.getLogger(__name__)


class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'llmstack.apps'
    label = 'apps'

    def ready(self) -> None:
        app_types = []
        for subclass in AppTypeInterface.__subclasses__():
            try:
                app_types.append({
                    'slug': subclass.slug(),
                    'name': subclass.name(),
                    'description': subclass.description(),
                })
            except Exception as e:
                logger.error(
                    f"Error while loading app type: {subclass.slug()}")
                pass

        # If app slug is already present, do not add it again
        from llmstack.apps.models import AppType

        for app_type in app_types:
            if AppType.objects.filter(slug=app_type['slug']).exists():
                continue
            AppType.objects.create(**app_type)
            logger.info(f"Added App Type: {app_type['slug']}")
