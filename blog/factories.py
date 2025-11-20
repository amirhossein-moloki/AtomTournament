import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

from blog.models import (
    AuthorProfile, Category, Tag, Media, Post, Comment, Revision, Reaction,
    Page, Menu, MenuItem, Series
)

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('phone_number',)

    username = factory.LazyAttribute(lambda _: fake.user_name())
    email = factory.LazyAttribute(lambda _: fake.email())
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    phone_number = factory.Sequence(lambda n: f'+98912{n:07d}')
    is_staff = False


class AuthorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthorProfile
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(lambda o: o.user.get_full_name())
    bio = factory.LazyAttribute(lambda _: fake.paragraph())


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.LazyAttribute(lambda _: fake.word())
    slug = factory.Sequence(lambda n: f'{fake.slug()}-{n}')
    description = factory.LazyAttribute(lambda _: fake.sentence())


class SeriesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Series

    title = factory.LazyAttribute(lambda _: fake.sentence())
    slug = factory.LazyAttribute(lambda o: fake.slug(o.title))
    description = factory.LazyAttribute(lambda _: fake.paragraph())


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Page

    title = factory.LazyAttribute(lambda _: fake.sentence())
    slug = factory.LazyAttribute(lambda o: fake.slug(o.title))
    content = factory.LazyAttribute(lambda _: fake.text())
    status = 'published'


class MenuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Menu

    name = factory.LazyAttribute(lambda _: fake.word())
    location = factory.Iterator([choice[0] for choice in Menu.LOCATION_CHOICES])


class MenuItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuItem

    menu = factory.SubFactory(MenuFactory)
    label = factory.LazyAttribute(lambda _: fake.word())
    url = factory.LazyAttribute(lambda _: fake.uri())


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    title = factory.LazyAttribute(lambda _: fake.sentence())
    slug = factory.LazyAttribute(lambda o: fake.slug(o.title))
    excerpt = factory.LazyAttribute(lambda _: fake.paragraph())
    content = factory.LazyAttribute(lambda _: fake.text())
    reading_time_sec = factory.LazyAttribute(lambda _: fake.random_int(min=60, max=600))
    status = 'published'
    visibility = 'public'
    published_at = factory.LazyAttribute(
        lambda o: timezone.now() if o.status == 'published' else None
    )
    author = factory.SubFactory(AuthorProfileFactory)
    category = factory.SubFactory(CategoryFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            self.tags.add(TagFactory())


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    post = factory.SubFactory(PostFactory)
    user = factory.SubFactory(UserFactory)
    content = factory.LazyAttribute(lambda _: fake.paragraph())
    status = 'approved'


class MediaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Media

    storage_key = factory.LazyAttribute(lambda _: fake.uuid4())
    url = factory.LazyAttribute(lambda _: fake.url())
    type = 'image'
    mime = 'image/jpeg'
    size_bytes = factory.LazyAttribute(lambda _: fake.random_int(min=1000, max=50000))
    alt_text = factory.LazyAttribute(lambda _: fake.sentence())
    title = factory.LazyAttribute(lambda _: fake.sentence())
    uploaded_by = factory.SubFactory(UserFactory)


class RevisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Revision

    post = factory.SubFactory(PostFactory)
    editor = factory.SubFactory(UserFactory)
    title = factory.LazyAttribute(lambda o: o.post.title)
    content = factory.LazyAttribute(lambda o: o.post.content)
    excerpt = factory.LazyAttribute(lambda o: o.post.excerpt)
    change_note = factory.LazyAttribute(lambda _: fake.sentence())


from django.contrib.contenttypes.models import ContentType

class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reaction

    user = factory.SubFactory(UserFactory)
    reaction = 'like'
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content_object)
    )
    object_id = factory.SelfAttribute('content_object.id')
    content_object = factory.SubFactory(PostFactory)


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.LazyAttribute(lambda _: fake.word())
    slug = factory.Sequence(lambda n: f'{fake.slug()}-{n}')
    description = factory.LazyAttribute(lambda _: fake.sentence())
