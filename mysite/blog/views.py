from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator, InvalidPage
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from .models import Post
from django.http import Http404
from django.views.generic import ListView
from .forms import CommentForm, EmailPostForm, SearchForm
from django.core.mail import send_mail
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import (
 SearchVector,
    SearchQuery,
    SearchRank
)
from django.contrib.postgres.search import TrigramSimilarity



def post_list(request, tag_slug=None):
    posts = Post.published.all()
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    paginator = Paginator(post_list, 9)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)    

    index = posts.number - 1
    max_index = len(paginator.page_range) 
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index 
    page_range = list(paginator.page_range)[start_index:end_index]
    return render(request,
                  'blog/list.html',
                  {'posts': posts,
                   'tag': tag,
                   'page_range': page_range}
            )

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             status=Post.Status.PUBLISHED,
                             slug=post,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    
     # List of active comments for this post
    comments = post.comments.filter(active=True)


    # Pagination for comments
    comments_pagination = post.comments.filter(active=True)
    paginator_comments = Paginator(comments_pagination, 5)
    page_number = request.GET.get('page', 1)
    try:
        comments = paginator_comments.page(page_number)
    except PageNotAnInteger:
        comments = paginator_comments.page(1)
    except EmptyPage:
        comments = paginator_comments.page(paginator_comments.num_pages)    

    index = comments.number - 1
    max_index = len(paginator_comments.page_range) 
    start_index = index - 3 if index >= 3 else 0
    end_index = index + 3 if index <= max_index - 3 else max_index 
    page_range_comment = list(paginator_comments.page_range)[start_index:end_index]


    # Form for users to comment
    form = CommentForm()

     # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(
        tags__in=post_tags_ids
    ).exclude(id=post.id)
    similar_posts = similar_posts.annotate(
        same_tags=Count('tags')
    ).order_by('-same_tags', '-publish')[:4]
                            
    return render(request,
                  'blog/detail.html',
                  {'post': post,
                   'comments': comments,
                   'form': form,
                   'similar_posts': similar_posts,
                   'page_range_comment': page_range_comment}
    )

class PostListView(ListView):
    """
    Alternative post list view
    """
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/list.html'

def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            # ... send email
            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )
            subject = (f"{cd['name']} ({cd['email']}) "
                       f"recommends you read {post.title}"
            )
            message = (f"Read {post.title} at {post_url}\n\n"
                       f"{cd['name']}\'s comments: {cd['comments']}"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd['to']]
            )
            sent = True
    else:
        form = EmailPostForm()
    return render(request,
                  'blog/share.html',
                  {'post': post,
                   'form': form,
                   'sent': sent})

@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    comment = None
    # A comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create a Comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the comment to the database
        comment.save()
    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
            'form': form,
            'comment': comment
        },
    )


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = (
                Post.published.annotate(
                    similarity=TrigramSimilarity('title', query),
                )
                .filter(similarity__gt=0.1)
                .order_by('-similarity')
            )

    return render(
        request,
        'blog/search.html',
        {
            'form': form,
            'query': query,
            'results': results
        },
    )