from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Exists, OuterRef, Count
from django.utils.timezone import localtime
from application.models import AllPosts, Watchlist, UserProfile, Comment, PostLike, CommentLike
from django.contrib import messages
import requests, re, json, difflib


# Create your views here.
@login_required(login_url='login')
def index(request):
    posts = AllPosts.objects.all().order_by('-created_at')

    if request.user.is_authenticated:
        # Annotate each post with:
        # - whether the current user liked it
        # - number of comments
        posts = posts.annotate(
            liked=Exists(
                PostLike.objects.filter(user=request.user, post=OuterRef("pk"))
            ),
            comments_count=Count("comments", distinct=True)  # <-- comment count here
        )

        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_name = request.user
    else:
        user_name = None
        user_profile = None


    return render(request, 'home.html', {
        'posts': posts,
        'has_more_posts': False,
        'user_img': user_profile,
        'user_name': user_name,
    })

@login_required(login_url='login')
def explore(request):
    anime_genres = ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Thriller"]
    years = list(range(2025, 1994, -1))
    ratings = ['5.0+', '6.0+', '7.0+', '8.0+', '9.0+']
    statuses = ['Upcoming', 'Ongoing', 'Completed']

    # Genre, rating, status mappings
    GENRE_MAPPING = {
        "Action": 1, "Adventure": 2, "Comedy": 4, "Drama": 8,
        "Fantasy": 10, "Romance": 22, "Sci-Fi": 24, "Thriller": 41
    }
    RATING_MAPPING = {
        "5.0+": 5, "6.0+": 6, "7.0+": 7, "8.0+": 8, "9.0+": 9
    }
    STATUS_MAPPING = {
        "completed": "complete", "upcoming": "upcoming", "ongoing": "airing"
    }
    STATUS_COLOR_MAP = {
        "Finished Airing": {'label': 'completed', 'class': 'bg-green-600'},
        "Currently Airing": {'label': 'ongoing', 'class': 'bg-blue-600'},
        "Not yet aired": {'label': 'upcoming', 'class': 'bg-yellow-600'},
    }

    # Same mappings and lists...
    search_title = request.GET.get('search', '')
    genre = request.GET.get('genre', '')
    year = request.GET.get('year', '')
    rating = request.GET.get('rating', '')
    status = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'popularity')
    active_filters = [(field, request.GET.get(field)) for field in ['genre', 'year', 'rating', 'status'] if request.GET.get(field)]
    params = {}
    if sort_by == 'popularity':
        params['order_by'] = 'members'
        params['sort'] = 'desc'
    elif sort_by == 'rating':
        params['order_by'] = 'score'
        params['sort'] = 'desc'
    elif sort_by == 'year':
        params['order_by'] = 'start_date'
        params['sort'] = 'desc'
    elif sort_by == 'title':
        params['order_by'] = 'title'
        params['sort'] = 'asc'

    if search_title:
        params['q'] = search_title
    if genre and genre.title() in GENRE_MAPPING:
        params['genres'] = GENRE_MAPPING[genre.title()]
    if year:
        params['start_date'] = f"{year}-01-01"
        params['end_date'] = f"{year}-12-31"
    if rating and rating in RATING_MAPPING:
        params['min_score'] = RATING_MAPPING[rating]
    if status and status.lower() in STATUS_MAPPING:
        params['status'] = STATUS_MAPPING[status.lower()]

    if params:
        params['sfw'] = 'true'
        response = requests.get("https://api.jikan.moe/v4/anime", params=params)
        if response.status_code == 200:
            raw_anime = response.json().get('data', [])
            unique_anime_map = {}
            for anime in raw_anime:
                mal_id = anime.get('mal_id')
                if mal_id and mal_id not in unique_anime_map:
                    unique_anime_map[mal_id] = anime
            anime_data = list(unique_anime_map.values())[:24]
        else:
            anime_data = []

        pagination_info = response.json().get('pagination', {})
    else:
        response = requests.get("https://api.jikan.moe/v4/top/anime", params={'sfw': 'true'})
        if response.status_code == 200:
            raw_anime = response.json().get('data', [])
            unique_anime_map = {}
            for anime in raw_anime:
                mal_id = anime.get('mal_id')
                if mal_id and mal_id not in unique_anime_map:
                    unique_anime_map[mal_id] = anime
            anime_data = list(unique_anime_map.values())[:24]
        else:
            anime_data = []
        pagination_info = response.json().get('pagination', {})

    # Get user watchlist and favorites
    user_watchlist = Watchlist.objects.filter(user=request.user)
    watchlist_ids = set(user_watchlist.values_list('mal_id', flat=True))
    fav_ids = set(user_watchlist.filter(is_favorite=True).values_list('mal_id', flat=True))

    for anime in anime_data:
        status = anime.get('status', 'unknown')
        anime['status_color'] = STATUS_COLOR_MAP.get(status, {'label': 'unknown', 'class': 'bg-gray-500'})
        anime['is_in_watchlist'] = int(anime['mal_id']) in watchlist_ids
        anime['is_favorite'] = int(anime['mal_id']) in fav_ids

    total_animes = pagination_info.get('items', {}).get('total', 0)

    context = {
        'search_title': search_title,
        'anime_list': anime_data,
        'total_results': total_animes,
        'genres': anime_genres,
        'sort_by': sort_by,
        'years': years,
        'ratings': ratings,
        'statuses': statuses,
        'active_filters': active_filters,
        'has_next_page': pagination_info.get('has_next_page', False),
        'next_api_page': pagination_info.get('current_page', 1) + 1 if pagination_info.get('has_next_page') else None,
    }

    return render(request, 'explore.html', context)


@login_required(login_url='login')
def fetch_more_anime(request):
    page = request.GET.get('page')
    search = request.GET.get("search")
    genre = request.GET.get("genre")
    year = request.GET.get("year")
    rating = request.GET.get("rating")
    status = request.GET.get("status")
    params = {'page': page,'sfw': 'true'}
    # Genre, rating, status mappings
    GENRE_MAPPING = {
        "Action": 1, "Adventure": 2, "Comedy": 4, "Drama": 8,
        "Fantasy": 10, "Romance": 22, "Sci-Fi": 24, "Thriller": 41
    }
    RATING_MAPPING = {
        "5.0+": 5, "6.0+": 6, "7.0+": 7, "8.0+": 8, "9.0+": 9
    }
    STATUS_MAPPING = {
        "completed": "complete", "upcoming": "upcoming", "ongoing": "airing"
    }

    sort_by = request.GET.get('sort', 'popularity')

    if sort_by == 'popularity':
        params['order_by'] = 'members'
        params['sort'] = 'desc'
    elif sort_by == 'rating':
        params['order_by'] = 'score'
        params['sort'] = 'desc'
    elif sort_by == 'year':
        params['order_by'] = 'start_date'
        params['sort'] = 'desc'
    elif sort_by == 'title':
        params['order_by'] = 'title'
        params['sort'] = 'asc'

    if search:
        params['q'] = search
    if genre and genre.title() in GENRE_MAPPING:
        params['genres'] = GENRE_MAPPING[genre.title()]
    if year:
        params['start_date'] = f"{year}-01-01"
        params['end_date'] = f"{year}-12-31"
    if rating and rating in RATING_MAPPING:
        params['min_score'] = RATING_MAPPING[rating]
    if status and status.lower() in STATUS_MAPPING:
        params['status'] = STATUS_MAPPING[status.lower()]

    # selecting correct url for sending request
    if search or genre or year or rating or status:
        response = requests.get("https://api.jikan.moe/v4/anime", params=params)
    else:
        response = requests.get("https://api.jikan.moe/v4/top/anime", params=params)
    data = response.json().get('data', []) if response.status_code == 200 else []
    user_watchlist = Watchlist.objects.filter(user=request.user)
    watchlist_ids = set(user_watchlist.values_list('mal_id', flat=True))
    fav_ids = set(user_watchlist.filter(is_favorite=True).values_list('mal_id', flat=True))
    STATUS_COLOR_MAP = {
        "Finished Airing": {'label': 'completed', 'class': 'bg-green-600'},
        "Currently Airing": {'label': 'ongoing', 'class': 'bg-blue-600'},
        "Not yet aired": {'label': 'upcoming', 'class': 'bg-yellow-600'},
    }
    for anime in data:
        status = anime.get('status', 'unknown')
        anime['status_color'] = STATUS_COLOR_MAP.get(status, {'label': 'unknown', 'class': 'bg-gray-500'})
        anime['is_in_watchlist'] = int(anime['mal_id']) in watchlist_ids
        anime['is_favorite'] = int(anime['mal_id']) in fav_ids

    # Assume Jikan API returns pagination info like total pages or next_page
    pagination_info = response.json().get('pagination', {})
    has_next = pagination_info.get('has_next_page', False)
    next_api_page = int(page) + 1 if has_next else None

    return JsonResponse({
        'anime': data,
        'has_next': has_next,
        'next_api_page': next_api_page
    })



@login_required(login_url='login')
def my_watchlist(request):
    user_watchlist = Watchlist.objects.filter(user=request.user)
    length_of_watchlist = len(user_watchlist)
    return render(request, 'watchlist.html', {'watchlist': user_watchlist,'watchlist_length': length_of_watchlist})

@login_required(login_url='login')
def profile(request):
    user = request.user
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_watchlist = Watchlist.objects.filter(user=request.user)
    completed_animes = Watchlist.objects.filter(user=request.user,status='completed')
    plan_to_watch_animes = Watchlist.objects.filter(user=request.user,status='plan_to_watch')
    watching_animes = Watchlist.objects.filter(user=request.user,status='watching')
    dropped_animes = Watchlist.objects.filter(user=request.user,status='dropped')
    total_episodes = Watchlist.objects.filter(user=request.user, status='completed').aggregate(total=Sum('total_episodes'))['total'] or 0
    favorite_animes = Watchlist.objects.filter(user=request.user, is_favorite=True)
    return render(request, "profile.html", {
        "user": user,
        "user_profile": user_profile,
        "length_of_watchlist": len(user_watchlist),
        "completed_animes": len(completed_animes),
        "watching_animes": len(watching_animes),
        "plan_to_watch_animes": len(plan_to_watch_animes),
        "dropped_animes": len(dropped_animes),
        "total_episodes":total_episodes,
        "favorite_anime": favorite_animes
    })

@login_required(login_url='login')
@require_POST
def new_post(request):
    post_content = request.POST.get('content')
    if post_content:
        AllPosts.objects.create(user=request.user,avatar_url="static/images/profile_pics/img.png" ,content=post_content)
    return redirect('home')

@login_required(login_url='login')
def anime_details(request, anime_id):
    anime_detail = requests.get(f'https://api.jikan.moe/v4/anime/{anime_id}').json()
    anime_characters = requests.get(f'https://api.jikan.moe/v4/anime/{anime_id}/characters').json()
    is_added = Watchlist.objects.filter(mal_id=anime_id).first()
    is_fav = Watchlist.objects.filter(mal_id=anime_id, is_favorite=True).first()
    data = anime_detail.get('data', [])
    trailer_url = data['trailer']['url']
    print(trailer_url)
    return render(request, 'anime_details.html', {'anime':anime_detail['data'], 'trailer_url': trailer_url, 'anime_characters':anime_characters['data'][:10], 'is_added':is_added,"is_fav": is_fav, "malId": anime_id })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        user_username = request.POST['username']
        password = request.POST['password']
        try:
            if '@' in user_username:
                user = User.objects.get(email=user_username)
            else:
                user = User.objects.get(username=user_username)
        except User.DoesNotExist:
            messages.error(request, "Can't find account with this username. Create a new account.")
            return redirect('signup')
        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Password is incorrect.')
            return redirect('login')
    return render(request, template_name='login.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if not username or not email or not password or not confirm_password:
            messages.error(request, 'All fields are required.')
            return render(request, 'signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'signup.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Invalid email format.")
            return redirect('signup')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'signup.html')

        if not re.search(r"\d", password):
            messages.error(request, "Password must include at least one number.")
            return render(request, 'signup.html')

        if not re.search(r"[^\w\s]", password):
            messages.error(request, "Password must include at least one special character.")
            return render(request, 'signup.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')

        new_user = User.objects.create_user(username=username, email=email, password=password)
        new_user.save()

        messages.success(request, "Account created successfully!")
        return redirect(login_view)
    return render(request, template_name='signup.html')

@login_required(login_url='login')
def logout_view(request):
    logout(request)
    messages.success(request, "You've been logged out.")
    return redirect(login_view)

def check_username(request):
    username = request.GET.get('username', '')
    exists = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': exists})

@require_POST
@login_required(login_url='login')
def add_to_watchlist(request):
    mal_id = request.POST.get('mal_id')

    # Validate mal_id
    if not mal_id or not mal_id.isdigit():
        return JsonResponse({'message': 'Invalid MAL ID'}, status=400)

    # Check if already exists
    if Watchlist.objects.filter(user=request.user, mal_id=mal_id).exists():
        return JsonResponse({'message': 'Already added'}, status=400)

    try:
        # Fetch anime data
        response = requests.get(f'https://api.jikan.moe/v4/anime/{mal_id}')
        response.raise_for_status()
        anime_data = response.json().get('data')
    except (requests.RequestException, KeyError):
        return JsonResponse({'message': 'Failed to fetch anime data'}, status=500)

    # Status mapping
    status_map = {
        "Finished Airing": {'label': 'completed', 'class': 'bg-green-600'},
        "Currently Airing": {'label': 'ongoing', 'class': 'bg-blue-600'},
        "Not yet aired": {'label': 'upcoming', 'class': 'bg-yellow-600'},
    }
    status = anime_data.get('status', 'unknown')
    anime_data['status_color'] = status_map.get(status, {'label': 'unknown', 'class': 'bg-gray-500'})

    episodes = anime_data.get('episodes') or 0
    # Save to DB
    Watchlist.objects.create(
        user=request.user,
        mal_id=mal_id,
        title=anime_data.get('title_english') or anime_data.get('title'),
        image_url=anime_data.get('images', {}).get('webp', {}).get('large_image_url'),
        status=anime_data['status_color']['label'],
        rating=anime_data.get('score'),
        total_episodes = episodes
    )

    return JsonResponse({'message': 'Anime added to watchlist ✅'}, status=201)

@require_POST
@login_required
def toggle_favorite(request):
    mal_id = request.POST.get('mal_id')

    if not mal_id or not mal_id.isdigit():
        return JsonResponse({'error': 'Invalid MAL ID'}, status=400)

    try:
        # Try to get the anime from the user's watchlist
        anime = Watchlist.objects.get(user=request.user, mal_id=mal_id)

    except Watchlist.DoesNotExist:
        # If not in watchlist, fetch from API and create it with is_favorite=True
        try:
            response = requests.get(f'https://api.jikan.moe/v4/anime/{mal_id}')
            response.raise_for_status()
            anime_data = response.json().get('data')
        except (requests.RequestException, KeyError):
            return JsonResponse({'error': 'Failed to fetch anime data'}, status=500)

        # Status mapping
        status_map = {
            "Finished Airing": {'label': 'completed', 'class': 'bg-green-600'},
            "Currently Airing": {'label': 'ongoing', 'class': 'bg-blue-600'},
            "Not yet aired": {'label': 'upcoming', 'class': 'bg-yellow-600'},
        }
        status = anime_data.get('status', 'unknown')
        status_color = status_map.get(status, {'label': 'unknown', 'class': 'bg-gray-500'})

        # Create new Watchlist entry with is_favorite=True
        anime = Watchlist.objects.create(
            user=request.user,
            mal_id=mal_id,
            title=anime_data.get('title_english') or anime_data.get('title'),
            image_url=anime_data.get('images', {}).get('webp', {}).get('large_image_url'),
            status=status_color['label'],
            rating=anime_data.get('score'),
            is_favorite=True
        )
        return JsonResponse({'favorited': True, 'message': 'Anime added to watchlist and marked as favorite'})

    # If already in watchlist, toggle favorite
    anime.is_favorite = not anime.is_favorite
    anime.save()
    return JsonResponse({'favorited': anime.is_favorite})

@csrf_exempt
@require_POST
@login_required(login_url='login')
def delete_anime(request, anime_id):
    if request.method == "POST":
        try:
            anime = Watchlist.objects.get(user=request.user, mal_id=anime_id)
            anime.delete()
            return JsonResponse({'success': True})
        except Watchlist.DoesNotExist:
            return JsonResponse({'error': 'Anime not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@require_POST
@login_required(login_url='login')
def add_or_update_anime(request):
    if request.method == 'POST':
        try:
            image_url = None
            episodes = None
            data = json.loads(request.body)
            mal_id = data.get('mal_id')
            title = data.get('title')
            status = data.get('status')
            rating = data.get('rating')
            is_exist = data.get('is_exist')

            if not title:
                return JsonResponse({'success': False, 'error': 'Anime title is required'}, status=400)

            # If anime doesn't exist, search from Jikan
            if not is_exist:
                # If no MAL ID, try to find it from Jikan API
                if not mal_id:
                    # Prevent duplicate entries for this user
                    if Watchlist.objects.filter(user=request.user, title=title).exists():
                        return JsonResponse({
                            'success': False,
                            'message': "Anime already exists",
                            'anime_id': None,
                            "title": title
                        })

                    # Jikan API Search
                    jikan_url = f'https://api.jikan.moe/v4/anime?q={title}&type=tv&limit=5'
                    response = requests.get(jikan_url)

                    if response.status_code != 200:
                        return JsonResponse({'success': False, 'error': 'Failed to retrieve anime.'}, status=500)

                    results = response.json().get('data', [])

                    if not results:
                        return JsonResponse({'success': False, 'error': 'No matching anime found'}, status=404)

                    # Find best match
                    best_match = max(
                        results,
                        key=lambda anime: difflib.SequenceMatcher(
                            None, title.lower(), (anime.get('title_english') or anime.get('title')).lower()
                        ).ratio()
                    )
                    title = best_match.get('title_english') or best_match.get('title')
                    mal_id = best_match.get('mal_id')
                    image_url = best_match['images']['webp']['large_image_url']
                    episodes = best_match.get('episodes') or 0

            # Update or Add Anime
            defaults = {
                'title': title,
                'status': status,
                'rating': rating,
            }
            if image_url:
                defaults['image_url'] = image_url

            if episodes:
                defaults['total_episodes'] = episodes

            watchlist_item, created = Watchlist.objects.update_or_create(
                user=request.user,
                mal_id=mal_id,
                defaults=defaults
            )

            return JsonResponse({
                'success': True,
                'is_update': True if not created else False,
                'anime_id': watchlist_item.id,
                'mal_id': mal_id,
                'title': title,
                'image_url': watchlist_item.image_url,
                'status': status,
                'rating': rating,
                'date': localtime(watchlist_item.added_at).strftime("%#d/%#m/%Y")
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_exempt
@require_POST
@login_required(login_url='login')
def edit_profile(request):
    user = request.user
    name = request.POST.get('display_name')
    username = request.POST.get('username')
    location = request.POST.get('location')
    bio = request.POST.get('bio')
    profile_pic = request.FILES.get('profile_picture')
    show_email = request.POST.get('show_email')

    if User.objects.filter(username=username).exists() and username != user.username:
        messages.error(request, "Username already taken.")
        return redirect('profile')

    # update inbuild user table
    user.username = username
    user.first_name = name
    user.save()
    # If UserProfile doesn't exist for this user, create a blank one
    profile, created = UserProfile.objects.get_or_create(user=user)
    # updating custom userProfile table
    profile.bio = bio
    profile.location = location
    profile.profile_picture = profile_pic
    profile.show_email = True if show_email == "on" else False
    profile.save()

    return redirect('profile')

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(AllPosts, id=post_id)
    # Allow if the user is the owner OR is superuser
    if request.user == post.user or request.user.is_superuser:
        post.delete()
        return redirect('home')  # redirect to your homepage
    else:
        return HttpResponseForbidden("You are not allowed to delete this post.")



@login_required
def post_detail(request, post_id):
    """Display a single post with its comments."""
    post = get_object_or_404(AllPosts, id=post_id)

    # Check if current user has liked the post
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = PostLike.objects.filter(user=request.user, post=post).exists()
    # Get profile picture from DB if user has one
    user_img = None
    user_name = None
    if request.user.is_authenticated:
        user_name = request.user.username
        try:
            profile = UserProfile.objects.get(user=request.user)  # fetch from DB
            if profile.profile_picture:
                user_img = profile.profile_picture.url  # actual image URL from DB
        except UserProfile.DoesNotExist:
            user_img = None  # no profile found

    # Get all comments for this post, ordered by newest first
    # comments = post.comments.all().order_by('-created_at')
    context = {
        'post': post,
        'user_has_liked': user_has_liked,
        'user_img': user_img,
        'user_name': user_name,
    }

    return render(request, 'post_detail.html', context)


@login_required
@require_POST
def add_comment(request, post_id):
    """Add a comment to a post."""
    post = get_object_or_404(AllPosts, id=post_id)
    content = request.POST.get('content', '').strip()

    if content and len(content) <= 280:
        comment = Comment.objects.create(
            post=post,
            user=request.user,
            content=content
        )
        # Optional: Add notification to post owner
        if post.user != request.user:
            # Create notification logic here
            pass

    return redirect('post_detail', post_id=post_id)


@login_required
@require_POST
def delete_comment(request, comment_id):
    """Delete a comment if user is the owner."""
    comment = get_object_or_404(Comment, id=comment_id)
    post_id = comment.post.id

    # Only allow comment owner to delete
    if comment.user == request.user:
        comment.delete()

    return redirect('post_detail', post_id=post_id)


@login_required
@require_POST
def toggle_like(request, post_id):
    """Toggle like status for a post (AJAX endpoint)."""
    post = get_object_or_404(AllPosts, id=post_id)

    # Check if user already liked the post
    like = PostLike.objects.filter(user=request.user, post=post).first()

    if like:
        # Unlike the post
        like.delete()
        post.likes_count = PostLike.objects.filter(post=post).count()
        post.save(update_fields=["likes_count"])
        liked = False
    else:
        # Like the post
        PostLike.objects.create(user=request.user, post=post)  # ✅ use PostLike
        post.likes_count = PostLike.objects.filter(post=post).count()
        post.save(update_fields=["likes_count"])
        liked = True

    # Get updated like count
    likes_count = post.likes.count()

    return JsonResponse({
        "liked": liked,
        "likes_count": post.likes_count
    })

