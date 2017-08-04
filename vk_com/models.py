from django.db import models


class VkAccess(models.Model):
    vk_group_id = models.CharField(max_length=100)
    vk_user_id = models.CharField(max_length=100)
    vk_client_id = models.CharField(max_length=100)
    vk_client_secret = models.CharField(max_length=100)
    vk_service_secret = models.CharField(max_length=100)
    vk_access_token = models.CharField(max_length=100, null=True)


class NewsForVk(models.Model):
    title = models.CharField(max_length=255)
    news_id = models.IntegerField()
    is_published = models.BooleanField(default=False)
    vk_post_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '%s' % self.title
