from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.views.generic import ListView, DetailView
from .models import Post
from .forms import CommentForm


def post_detail_redirect(request, slug):
    return redirect(reverse('post_detail', kwargs={'slug': slug}), permanent=True)


class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'

    def get_queryset(self):
        try:
            return Post.objects.published().order_by('-published_at', '-id')
        except Exception as e:
            messages.error(self.request, "خطایی در هنگام بارگذاری لیست پست‌ها رخ داد.")
            return Post.objects.none()


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return Post.objects.published()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.filter(is_approved=True)
        return context

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.post = self.object
                comment.user = request.user
                comment.save()
                messages.success(request, "نظر شما با موفقیت ثبت شد و پس از تایید نمایش داده خواهد شد.")
                return redirect(self.object.get_absolute_url())
            else:
                # اگر فرم نامعتبر بود، پیام خطا را نمایش بده
                error_message = "خطا در ثبت نظر: " + " ".join([f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()])
                messages.error(request, error_message)

        except Exception as e:
            messages.error(self.request, f"یک خطای پیش‌بینی نشده در هنگام ثبت نظر رخ داد: {e}")

        # در صورت خطا یا نامعتبر بودن فرم، به همان صفحه برگرد
        context = self.get_context_data()
        context['form'] = form if 'form' in locals() else CommentForm()
        return self.render_to_response(context)
