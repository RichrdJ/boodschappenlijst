"""Inloggen met Google of Apple (OpenID Connect). Er worden geen wachtwoorden bewaard.

Google:  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
Apple:   APPLE_CLIENT_ID (Services ID), APPLE_TEAM_ID, APPLE_KEY_ID,
         APPLE_PRIVATE_KEY (inhoud van het .p8-bestand) of APPLE_PRIVATE_KEY_FILE
Alleen lokaal testen: DEV_LOGIN=1 geeft een inlogknop zonder controle. Nooit publiek aanzetten.
"""
import json
import logging
import os
import secrets
import time

from authlib.integrations.flask_client import OAuth, OAuthError
from authlib.jose import jwt
from flask import Blueprint, abort, redirect, render_template, request, session

log = logging.getLogger("boodschappen.auth")
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()
_login_user = None

GOOGLE = bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))
APPLE = bool(os.environ.get("APPLE_CLIENT_ID") and os.environ.get("APPLE_TEAM_ID") and os.environ.get("APPLE_KEY_ID")
             and (os.environ.get("APPLE_PRIVATE_KEY") or os.environ.get("APPLE_PRIVATE_KEY_FILE")))
DEV = os.environ.get("DEV_LOGIN") == "1"
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")


def enabled_providers():
    return {"google": GOOGLE, "apple": APPLE, "dev": DEV}


def allowed(email):
    """Optioneel: ALLOWED_EMAILS=jij@gmail.com,partner@icloud.com,@familie.nl"""
    rules = [r.strip().lower() for r in os.environ.get("ALLOWED_EMAILS", "").split(",") if r.strip()]
    if not rules:
        return True
    email = (email or "").lower()
    return any(email == r or (r.startswith("@") and email.endswith(r)) for r in rules)


def apple_client_secret():
    """Apple wil als client secret een door ons ondertekende JWT (max. 6 maanden geldig); we maken er steeds een verse."""
    key = os.environ.get("APPLE_PRIVATE_KEY")
    if not key:
        with open(os.environ["APPLE_PRIVATE_KEY_FILE"]) as f:
            key = f.read()
    now = int(time.time())
    claims = {"iss": os.environ["APPLE_TEAM_ID"], "iat": now, "exp": now + 600,
              "aud": "https://appleid.apple.com", "sub": os.environ["APPLE_CLIENT_ID"]}
    return jwt.encode({"alg": "ES256", "kid": os.environ["APPLE_KEY_ID"]}, claims, key.replace("\\n", "\n")).decode()


def init_auth(app, login_user):
    global _login_user
    _login_user = login_user
    oauth.init_app(app)
    if GOOGLE:
        oauth.register("google", client_id=os.environ["GOOGLE_CLIENT_ID"], client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                       server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                       client_kwargs={"scope": "openid email profile"})
    if APPLE:
        oauth.register("apple", client_id=os.environ["APPLE_CLIENT_ID"],
                       server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
                       client_kwargs={"scope": "openid email name", "token_endpoint_auth_method": "client_secret_post"},
                       authorize_params={"response_mode": "form_post"})
    if DEV:
        log.warning("DEV_LOGIN staat aan: iedereen kan inloggen zonder controle. Alleen voor lokaal testen!")
    if not (GOOGLE or APPLE or DEV):
        log.warning("Geen inlogmethode ingesteld: zet GOOGLE_CLIENT_ID/SECRET en/of de APPLE_* variabelen")


def callback_url(provider):
    base = PUBLIC_URL or request.host_url.rstrip("/")
    return f"{base}/auth/{provider}/callback"


def finish(provider, subject, email, verified, name):
    if not allowed(email):
        return redirect("/?fout=toegang")
    join = session.get("join")
    _login_user(provider, subject, email, verified, name)
    return redirect(f"/join/{join}" if join else "/")


def fail(e):
    log.warning("Inloggen mislukt: %s", e)
    return redirect("/?fout=mislukt")


@auth_bp.get("/<provider>/login")
def login(provider):
    if provider not in ("google", "apple") or not enabled_providers()[provider]:
        abort(404)
    return oauth.create_client(provider).authorize_redirect(callback_url(provider))


@auth_bp.get("/google/callback")
def google_callback():
    if not GOOGLE:
        abort(404)
    try:
        info = oauth.google.authorize_access_token()["userinfo"]
    except (OAuthError, KeyError) as e:
        return fail(e)
    return finish("google", info["sub"], info.get("email"), info.get("email_verified") is True, info.get("name"))


@auth_bp.post("/apple/callback")
def apple_callback():
    """Apple stuurt het resultaat als POST vanaf appleid.apple.com. Onze sessiecookie (SameSite=Lax)
    gaat daar niet mee, dus sturen we het formulier één keer door vanaf onze eigen pagina."""
    if not APPLE:
        abort(404)
    fields = {k: request.form.get(k, "") for k in ("code", "state", "user", "error")}
    nonce = secrets.token_urlsafe(16)
    resp = render_template("relay.html", fields=fields, nonce=nonce)
    return resp, 200, {"Content-Security-Policy": f"default-src 'none'; script-src 'nonce-{nonce}'; form-action 'self'"}


@auth_bp.post("/apple/finish")
def apple_finish():
    if not APPLE:
        abort(404)
    if request.form.get("error"):
        return fail(request.form["error"])
    try:
        oauth.apple.client_secret = apple_client_secret()
        info = oauth.apple.authorize_access_token()["userinfo"]
    except (OAuthError, KeyError) as e:
        return fail(e)
    name = None
    try:  # alleen bij de allereerste keer stuurt Apple de naam mee
        n = json.loads(request.form.get("user") or "{}").get("name") or {}
        name = " ".join(x for x in (n.get("firstName"), n.get("lastName")) if x) or None
    except (ValueError, AttributeError):
        pass
    verified = info.get("email_verified") in (True, "true")
    return finish("apple", info["sub"], info.get("email"), verified, name)


@auth_bp.post("/dev/login")
def dev_login():
    if not DEV:
        abort(404)
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        return redirect("/")
    return finish("dev", email, email, True, email.split("@")[0])
