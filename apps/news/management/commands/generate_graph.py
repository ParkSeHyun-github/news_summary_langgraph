"""
python manage.py generate_graph
python manage.py generate_graph --output my_graph.png
"""
from django.core.management.base import BaseCommand
from apps.news.graph.builder import save_graph_image


class Command(BaseCommand):
    help = "LangGraph 구조를 graph.png 로 저장"

    def add_arguments(self, parser):
        parser.add_argument("--output", default="graph.png", help="저장 경로")

    def handle(self, *args, **options):
        save_graph_image(options["output"])
        self.stdout.write(self.style.SUCCESS(f"완료: {options['output']}"))
