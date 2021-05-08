from django.utils import timezone

from .models import Analyzer


def create_analyzer(user, data):

    available_sources = ['artist_url']
    method = 'get_by_'
    param = None

    for source, param in data.items():
        if source in available_sources and param:
            method += source
            param = param
            break

    method = 'get_by_chart' if method == 'get_by_' else method

    analyzer = Analyzer(owner=user,
                        status=3,
                        method=method,
                        param=param,
                        start_date=timezone.now())
    analyzer.save()

    return {'analyzer_id': analyzer.pk}


def delete_analyzer(user, data):
    analyzer = Analyzer.objects.filter(owner=user, pk=data['id']).first()
    if not analyzer:
        return {'error': f'not found or no permissions to analyzer with id {data["id"]}'}

    analyzer.delete()
    return {'response': f"analyzer with id {data['id']} was deleted"}


def save_analyzing_result(analyzer, result):
    if isinstance(result, dict):
        analyzer.status = 2
        analyzer.result = result
    else:
        analyzer.status = 0
        analyzer.error = 'Error with saving results'
    analyzer.finish_date = timezone.now()
    analyzer.save()
