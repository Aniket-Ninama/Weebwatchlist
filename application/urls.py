from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from application import views
urlpatterns = [
    path('login', views.login_view, name='login'),
    path('signup', views.signup_view, name='signup'),
    path('check-username/', views.check_username, name='check_username'),
    path('', views.index, name='home'),
    path('explore', views.explore, name='explore'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('fetch-more-anime', views.fetch_more_anime, name='fetch_more_anime'),
    path('watchlist', views.my_watchlist, name='watchlist'),
    path('profile', views.profile, name='profile'),
    path('edit-profile', views.edit_profile, name='edit-profile'),
    path('new-post', views.new_post, name='new_post'),
    path('add-to-watchlist/', views.add_to_watchlist, name='add_to_watchlist'),
    path('toggle-favorite/', views.toggle_favorite, name='add_to_favorite'),
    path('anime/<int:anime_id>/', views.anime_details, name='anime_details'),
    path('anime/add-or-update/', views.add_or_update_anime, name='add_or_update_anime'),
    path('delete-anime/<int:anime_id>/', views.delete_anime, name='delete_anime'),
    path('logout', views.logout_view, name='logout'),
    # For Development
    path("__reload__/", include('django_browser_reload.urls'))
]
# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
