from django.contrib import admin

from vk_com.models import NewsForVk


class NewsForVkAdmin(admin.ModelAdmin):
    list_display = ['title', 'news_id', 'vk_post_id', 'is_published']

    class Meta:
        model = NewsForVk

admin.site.register(NewsForVk, NewsForVkAdmin)
