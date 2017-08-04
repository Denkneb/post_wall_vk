from __future__ import absolute_import, unicode_literals

import logging
import os
import re

import django
import requests

from celery import Celery
import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from post_wall_vk.settings import BROKER_URL, BROKER_VHOST

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "post_wall_vk.settings")
django.setup()

from news.models import News, ImagesNews
from vk_com.models import VkAccess, NewsForVk

logger = logging.getLogger(__name__)

app = Celery('tasks', broker=BROKER_URL + BROKER_VHOST)
# app = Celery('tasks', broker='amqp://')

app.conf.beat_schedule = {
        'get_news_today': {
            'task': 'get_news_today',
            'schedule': datetime.timedelta(hours=3),
        },
        'post_wall_vk': {
            'task': 'post_wall_vk',
            'schedule': datetime.timedelta(hours=5),
        },
    }


@app.task(name='get_news_today')
def get_news_today():
    logger.info('Tasks running')

    news_today = News.objects.filter(pup_date__gte=timezone.now() - datetime.timedelta(days=1))
    for news in news_today:
        if not News.objects.filter(news_id=news.id):
            News.objects.create(
                title=news.title,
                news_id=news.id,
            )


def get_news_by_id(news_id):
    news = None
    try:
        news_by_id = News.objects.get(id=news_id)
        if news_by_id.is_active:
            news_image = ImagesNews.objects.filter(news_id=news_id).get(is_main=True)
            news = {
                'news_photo_url': '/webapps/django_site/kainsk_eparhia/static' + news_image.thumbnail.url,
                'news_text': re.sub(r'(<[^>]+>)', '', news_by_id.text[0:300]),
                'news_link': 'http://kainsk-eparhia.ru/{}/'.format(news_by_id.slug),
            }
    except ObjectDoesNotExist:
        NewsForVk.objects.filter(news_id=news_id).delete()

    return news


@app.task(name='post_wall_vk')
def post_wall_vk():
    logger.info('Tasks running')

    vk = VkAccess.objects.get()

    news_for_vk = NewsForVk.objects.filter(is_published=False)

    for news in news_for_vk:
        news_by_id = get_news_by_id(news.news_id)
        if news_by_id is not None:
            upload_server = requests.get('https://api.vk.com/method/photos.getWallUploadServer?group_id='
                                         + vk.vk_group_id +
                                         '&access_token=' + vk.vk_access_token +
                                         '&v=5.65'
                                         ).json()
            upload_url = upload_server['response']['upload_url']
            image = news_by_id['news_photo_url']
            file_ = {'photo': (image, open(image, 'rb'))}
            post_image = requests.post(upload_url, files=file_).json()

            save_image_url = 'https://api.vk.com/method/photos.saveWallPhoto?' \
                             'group_id=' + vk.vk_group_id + \
                             '&photo=' + str(post_image['photo']) + \
                             '&server=' + str(post_image['server']) + \
                             '&hash=' + str(post_image['hash']) + \
                             '&access_token=' + str(vk.vk_access_token) + \
                             '&v=5.65'
            save_image = requests.get(save_image_url).json()

            post_news_on_wall = requests.get('https://api.vk.com/method/wall.post?owner_id=-'
                                             + vk.vk_group_id +
                                             '&from_group=1'
                                             '&message={}\n{}...'.format(news.title, news_by_id['news_text']) +
                                             '&attachments=photo' +
                                             str(save_image['response'][0]['owner_id']) +
                                             '_' + str(save_image['response'][0]['id']) +
                                             ',' + news_by_id['news_link'] +
                                             '&access_token=' + str(vk.vk_access_token) +
                                             '&v=5.65').json()
            NewsForVk.objects.filter(id=news.id).update(is_published=True,
                                                        vk_post_id=post_news_on_wall['response']['post_id'])

    return len(news_for_vk)
