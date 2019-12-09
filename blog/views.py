from django.shortcuts import render, redirect, get_list_or_404
from django.http import HttpResponse
from .models import Articles, Link, Tag, Comment, Catalog
from django.templatetags.static import static
from django.template import defaultfilters
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Max, Count
import markdown
from jinja2 import Environment


def tp_reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, **kw):
    return reverse(viewname, urlconf=urlconf, args=args, kwargs=kw or kwargs, current_app=current_app)


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': tp_reverse,
        'dj': defaultfilters,
        'img': format_html
    })
    return env


def context(request):
    links = Link.objects.all()
    hot_articles = Articles.objects.filter(comment__id__isnull=False, active=True).annotate(
        comment_id=Max('comment__id')).order_by('-comment_id')[:6]
    catalogs = Catalog.objects.all()
    ctx = {
        'links': links,
        'hots': hot_articles,
        'catalogs': catalogs,
        'pagesize': 8,
        'page': int(request.GET.get('page', 1))
    }
    ctx.update({
        'from_page': ctx['pagesize'] * (ctx['page'] - 1),
        'to_page': ctx['pagesize'] * (ctx['page']),
        'next_page': ctx['pagesize'] * (ctx['page'] + 1)
    })
    return ctx


# Create your views here.
def page_500(request):
    return render(request, 'blog/404.html', context={'para': {}})


def page_404(request):
    return render(request, 'blog/404.html', context={'para': {}}, status=404)


def index(request):
    g = context(request)
    para = request.GET.dict()
    para = {'page': int(para.get('page', 1)),
            'url': para.get('url', 'index'),
            'title': para.get('title', '最新发布'), }
    articles = Articles.objects.filter(active=True)[g['from_page']:g['to_page']]
    recommands = Articles.objects.filter(active=True, recommand=True).order_by('order_id')
    rows_left = len(Articles.objects.filter(active=True)[g['next_page']:])
    g.update({'articles': articles,
              'recommands': recommands,
              'para': para,
              'left': rows_left})
    return render(request, 'blog/index.html', context=g)


def detail(request, num):
    g = context(request)
    para = request.GET.dict()
    para.update(request.POST.dict())
    article = Articles.objects.get(active=True, id=num)
    article.body = markdown.markdown(article.body, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ])

    if para.get('comment_submit') and para.get('comment') and para.get('username'):
        comment = Comment(body=para.get('comment'),
                          username=para.get('username'),
                          email=para.get('email'),
                          article_id=num)

        comment.save()
    article.visited += 1
    article.save()
    g.update({'article': article, 'para': para})
    return render(request, 'blog/detail.html', context=g)


def post_comment(request):
    para = request.POST.dict()
    if para.get('comment_submit') and para.get('comment') and para.get('username'):
        comment = Comment(body=para.get('comment'),
                          username=para.get('username'),
                          email=para.get('email'),
                          article_id=para.get('article_id'))

        comment.save()
        return redirect('/blog/detail/' + para.get('article_id'))


def catalog_list(request, catalog):
    g = context(request)
    para = request.GET.dict()
    catalog_name = g['catalogs'].get(name_eng=catalog).name if catalog != 'search' else catalog
    para.update({'title': catalog_name,
                 'page': int(para.get('page', 1)),
                 'catalog': catalog,
                 'url': catalog,
                 'tag': para.get('tag', '')})
    para.update(request.POST.dict())
    params_articles = {
        'tags__name': para.get('tag'),
        'name__contains' if para.get('keyword') else 'name': para.get('keyword', None),
        'catalog__name_eng': None if catalog == 'search' else catalog
    }
    params_articles = {k: v for k, v in params_articles.items() if v}
    articles = Articles.objects.filter(active=True, **params_articles)
    now_articles = articles[g['pagesize'] * (para['page'] - 1):g['pagesize'] * (para['page'])]
    rows_left = len(articles[g['pagesize'] * (para['page']) + 1:])

    params_tags = {
        'articles__name__contains' if para.get('keyword') else 'name': para.get('keyword', None),
        'articles__catalog__name_eng': None if catalog == 'search' else catalog
    }
    params_tags = {k: v for k, v in params_tags.items() if v}
    tags = Tag.objects.filter(**params_tags).annotate(count_id=Count('id')).order_by('-count_id')
    g.update({'articles': now_articles,
              'tags': tags,
              'para': para,
              'left': rows_left})
    return render(request, 'blog/list.html', context=g)


from dwebsocket import require_websocket


@require_websocket
def wb(request):
    import time
    message = request.websocket.wait()
    while 1:
        print(message)
        request.websocket.send(message)
        time.sleep(5)