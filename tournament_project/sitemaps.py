from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from tournaments.models import Tournament, Game


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Post.objects.published()

    def location(self, obj):
        return f"/blog/{obj.slug}"


class TournamentLobySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Tournament.objects.all()

    def location(self, obj):
        return f"/tournament-loby/{obj.slug}"


class TournamentResultSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Tournament.objects.all()

    def location(self, obj):
        return f"/tournament-result/{obj.slug}"


class GameTournamentsSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Game.objects.filter(status="active")

    def location(self, obj):
        return f"/game-tournaments/{obj.slug}"


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "/",
            "/leaderBoard",
            "/about",
            "/register/login",
            "/register/signup",
            "/user-dashboard/",
            "/user-dashboard/verification",
            "/user-dashboard/teams",
            "/user-dashboard/user-games",
            "/user-dashboard/tournaments",
            "/user-dashboard/wallet",
            "/user-dashboard/tickets",
            "/user-dashboard/chat",
        ]

    def location(self, item):
        return item
