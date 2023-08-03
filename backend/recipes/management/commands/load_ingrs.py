import csv

from django.conf import settings
from django.core.management import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Download csv"

    def handle(self, *args, **kwargs):
        d_path = settings.BASE_DIR
        with open(
            f"{d_path}/data/ingredients.csv", "r+", encoding="utf-8"
        ) as f:
            reader = csv.DictReader(f)
            Ingredient.objects.bulk_create(
                Ingredient(**data) for data in reader)
        self.stdout.write(self.style.SUCCESS("OK"))
