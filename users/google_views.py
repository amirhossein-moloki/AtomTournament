import secrets
import time
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponseRedirect

from users.models import User
from rest_framework_simplejwt.tokens import RefreshToken

import jwt
from jwt import InvalidTokenError

def build_google_auth_url(state: str):
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "state": state,
    }
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base}?{urlencode(params)}"

def exchange_code_for_tokens(code: str):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(token_url, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_google_jwks():
    jwks = cache.get("google_jwks")
    if jwks:
        return jwks
    resp = requests.get("https://www.googleapis.com/oauth2/v3/certs", timeout=10)
    resp.raise_for_status()
    jwks = resp.json()
    cache.set("google_jwks", jwks, 24 * 60 * 60)
    return jwks

def verify_id_token(id_token: str, audience: str):
    jwks = get_google_jwks()
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    key = None
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") == kid:
            key = jwk
            break
    if not key:
        raise InvalidTokenError("Unable to find matching JWK for token")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

    payload = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=audience,
        options={"verify_at_hash": False}
    )
    return payload

class GoogleLoginRedirect(APIView):
    def get(self, request):
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state
        request.session['google_oauth_state_ts'] = int(time.time())

        auth_url = build_google_auth_url(state)
        return HttpResponseRedirect(auth_url)

class GoogleCallback(APIView):
    def get(self, request):
        error = request.GET.get("error")
        if error:
            return Response({"detail": f"Google error: {error}"}, status=status.HTTP_400_BAD_REQUEST)

        code = request.GET.get("code")
        state = request.GET.get("state")
        saved_state = request.session.get('google_oauth_state')

        if not code or not state or not saved_state or state != saved_state:
            return Response({"detail": "Invalid state or missing code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            del request.session['google_oauth_state']
            del request.session['google_oauth_state_ts']
        except KeyError:
            pass

        try:
            token_data = exchange_code_for_tokens(code)
        except requests.HTTPError as exc:
            return Response({"detail": "Failed to exchange code for token", "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        id_token = token_data.get("id_token")
        if not id_token:
            return Response({"detail": "id_token not returned by Google"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = verify_id_token(id_token, audience=settings.GOOGLE_CLIENT_ID)
        except Exception as exc:
            return Response({"detail": "Invalid id_token", "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        email = payload.get("email")
        email_verified = payload.get("email_verified", False)
        if not email or not email_verified:
            return Response({"detail": "Google account email not available or not verified"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail": "Account does not exist"}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        response = HttpResponseRedirect(settings.FRONTEND_URL)
        response.set_cookie(
            key="access_token",
            value=access,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=60 * 60 * 24
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=60 * 60 * 24 * 7
        )

        response.set_cookie(
            key="user_email",
            value=email,
            httponly=False,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=60 * 60 * 24
        )

        return response
