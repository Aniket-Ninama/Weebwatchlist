from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
# Create your models here.

class AllPosts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    likes_count = models.PositiveBigIntegerField(default=0)
    share_count = models.PositiveBigIntegerField(default=0)

    @property
    def avatar_url(self):
        profile = getattr(self.user, "userprofile", None)
        if profile and profile.profile_picture:
            return profile.profile_picture.url
        # Fallback to static default
        return static('images/profile_pics/img.png')

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Post"
        verbose_name_plural = "Posts"


# New Comment model
class Comment(models.Model):
    post = models.ForeignKey(AllPosts, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    likes_count = models.PositiveBigIntegerField(default=0)

    @property
    def avatar_url(self):
        profile = getattr(self.user, "userprofile", None)
        if profile and profile.profile_picture:
            return profile.profile_picture.url
        # Fallback to static default
        return static('images/profile_pics/img.png')

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post}"

    class Meta:
        ordering = ['-created_at']


# New Like model for tracking who liked what
class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(AllPosts, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Prevent duplicate likes

    def __str__(self):
        return f"{self.user.username} likes {self.post}"


# Comment Like model (optional)
class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mal_id = models.IntegerField()
    title = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    is_favorite = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    total_episodes = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'mal_id')  # Prevent duplicates

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='cover_pics/', blank=True, null=True)
    bio = models.TextField(blank=True)
    location = models.TextField(blank=True)
    show_email = models.BooleanField(default=False)

    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return static('images/profile_pics/img.png')

    @property
    def cover_image_url(self):
        if self.cover_image:
            return self.cover_image.url
        return static('images/cover_pics/cover_page.jpg')