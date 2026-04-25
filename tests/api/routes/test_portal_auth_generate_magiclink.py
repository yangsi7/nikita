"""Tests for portal_auth.generate_magiclink_for_telegram_user (Spec 215 §7.6).

ACs:
- AC-1: end-user JWT returns 401 (service-role guard).
- AC-2: valid service-role call returns Pydantic GenerateMagiclinkResponse with
  verification_type taken VERBATIM from Supabase response (no normalization).
- AC-3: static-grep fixture asserts no 'magiclink' or 'signup' string literal in
  handler source outside Pydantic Literal[...] annotation (Testing H2).

Pattern: AsyncMock for DB session + AsyncMock for Supabase client; service-role
guard tested via Authorization header check.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# AC-3: static-grep — handler source must not hardcode the literal strings
# 'magiclink' / 'signup' on the FR-5 path. Allowed contexts: type annotations
# (`Literal["magiclink", "signup"]`), docstrings, and comments. Disallowed:
# any other string usage in handler logic.
# ---------------------------------------------------------------------------

HANDLER_PATH = (
    Path(__file__).resolve().parents[3]
    / "nikita"
    / "api"
    / "routes"
    / "portal_auth.py"
)


def test_handler_source_has_no_hardcoded_verification_type_literals():
    """Testing H2: verification_type must come VERBATIM from Supabase response.

    Scan handler source. Allow: Literal[...] annotations, docstrings, comments.
    Disallow: bare 'magiclink' / 'signup' literal usage in code.

    Two-layer enforcement (regex + AST) to defeat evasion via f-strings,
    `.format()`, string concatenation, or chr() construction.
    """
    source = HANDLER_PATH.read_text()

    # Layer 1: regex on stripped source (catches direct literals).
    # Strip allowed contexts:
    # 1. Pydantic Literal[...] annotations (multi-line via DOTALL)
    cleaned = re.sub(r"Literal\[[^\]]*\]", "", source, flags=re.DOTALL)
    # 2. Triple-quoted docstrings
    cleaned = re.sub(r'"""[\s\S]*?"""', "", cleaned)
    cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned)
    # 3. Single-line comments
    cleaned = re.sub(r"#[^\n]*", "", cleaned)
    matches = re.findall(r"['\"](magiclink|signup)['\"]", cleaned)
    assert matches == [], (
        f"Found hardcoded verification_type literal(s) in handler "
        f"outside annotation contexts: {matches}. "
        "Per Spec 215 §7.6 + Testing H2 the value must come VERBATIM "
        "from the Supabase generate_link response."
    )


def test_handler_ast_has_no_verification_type_literal_constants():
    """Testing H2 AST layer: walk parsed AST, fail on any Constant("magiclink"|
    "signup") whose enclosing scope is NOT a Literal[...] subscript or an
    f-string formatted-value (latter would be caught by other checks).

    Defeats evasion via f-strings, .format(), str concatenation, chr().

    KNOWN GAP (out of threat model): a constant assembled at runtime via
    bytes-list decode (e.g. ``bytes([109,97,103,...]).decode()``) does NOT
    parse to an ``ast.Constant`` and would slip both layers. Detecting that
    requires constant-folding at runtime which is paranoid for an internal
    service-role-only handler. If this code ever moves to a public surface,
    revisit by running the handler under a tracer that flags string
    materializations matching the forbidden set.
    """
    import ast

    forbidden = {"magiclink", "signup"}
    source = HANDLER_PATH.read_text()
    tree = ast.parse(source)

    # Build set of constant nodes that ARE inside a Literal[...] subscript.
    allowed_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            value = node.value
            is_literal = (
                (isinstance(value, ast.Name) and value.id == "Literal")
                or (isinstance(value, ast.Attribute) and value.attr == "Literal")
            )
            if is_literal:
                for child in ast.walk(node):
                    if isinstance(child, ast.Constant):
                        allowed_nodes.add(id(child))

    offenders: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in forbidden
            and id(node) not in allowed_nodes
        ):
            # docstrings: ast.Constant inside an Expr at module/class/function
            # body[0]; allow.
            if hasattr(node, "lineno"):
                offenders.append(
                    f"line {node.lineno}: ast.Constant({node.value!r})"
                )

    # Filter: docstrings appear as the first statement (Expr->Constant) in
    # module/class/function bodies. Build the set of docstring-Constant ids.
    docstring_ids: set[int] = set()
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(parent, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_ids.add(id(body[0].value))

    real_offenders = [
        line for line in offenders
        if not any(
            f"line {body0.lineno}" == line.split(":")[0]
            for parent in ast.walk(tree)
            if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            for body0 in (getattr(parent, "body", [None])[:1])
            if isinstance(body0, ast.Expr)
            and isinstance(body0.value, ast.Constant)
            and id(body0.value) in docstring_ids
        )
    ]

    assert not real_offenders, (
        f"AST layer Testing H2 violation: handler contains forbidden "
        f"string Constant nodes outside Literal[...] subscripts: "
        f"{real_offenders}. The verification_type value must be sourced "
        f"VERBATIM from the Supabase response — never typed as a "
        f"string literal in handler code."
    )


# ---------------------------------------------------------------------------
# AC-1 + AC-2: HTTP-level handler tests via FastAPI TestClient.
# ---------------------------------------------------------------------------


def _build_test_app():
    """Build a minimal FastAPI app wiring just the portal_auth router."""
    from nikita.api.routes.portal_auth import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")
    return app


def test_endpoint_rejects_non_service_role_jwt():
    """AC-1: end-user JWT (or missing/garbage) MUST return 401."""
    app = _build_test_app()
    client = TestClient(app)

    # No Authorization header → 401
    resp = client.post(
        "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
        json={"telegram_id": 42, "email": "user@example.com"},
    )
    assert resp.status_code == 401, resp.text

    # Garbage Bearer → 401
    resp = client.post(
        "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
        headers={"Authorization": "Bearer not-the-service-key"},
        json={"telegram_id": 42, "email": "user@example.com"},
    )
    assert resp.status_code == 401, resp.text


def test_endpoint_returns_verification_type_verbatim_from_supabase():
    """AC-2: valid service-role call returns verification_type VERBATIM.

    Mock Supabase admin.generate_link to return verification_type="signup".
    Assert the response body echoes "signup" (NOT "magiclink") and that the
    repo persistence call received "signup" verbatim.
    """
    from nikita.config.settings import get_settings

    settings = get_settings()
    service_key = "test-service-key-deadbeef"

    # Patch settings so the handler accepts our test key as service-role.
    with patch.object(settings, "supabase_service_key", service_key):
        app = _build_test_app()

        # Mock Supabase client
        fake_link_props = MagicMock()
        fake_link_props.action_link = "https://example.com/auth/confirm?token_hash=abc&type=signup"
        fake_link_props.hashed_token = "hash-deadbeef"
        fake_link_props.verification_type = "signup"  # <-- from Supabase verbatim

        fake_link_result = MagicMock()
        fake_link_result.properties = fake_link_props

        fake_supabase = MagicMock()
        fake_supabase.auth.admin.generate_link = AsyncMock(
            return_value=fake_link_result
        )

        # Mock repo
        fake_repo = AsyncMock()
        fake_repo.transition_to_magic_link_sent.return_value = "row-id"

        # FastAPI Depends() captures the function reference at module load,
        # so module-level patching of _get_repo_for_request doesn't reach
        # the resolved dep. Use the official escape hatch instead.
        from nikita.api.routes.portal_auth import _get_repo_for_request

        async def _override_repo():
            return fake_repo

        app.dependency_overrides[_get_repo_for_request] = _override_repo

        with patch(
            "nikita.api.routes.portal_auth.get_supabase_client",
            new=AsyncMock(return_value=fake_supabase),
        ):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
                headers={"Authorization": f"Bearer {service_key}"},
                json={"telegram_id": 42, "email": "user@example.com"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Verbatim from Supabase: "signup", not normalized to "magiclink"
        assert body["verification_type"] == "signup"
        assert body["hashed_token"] == "hash-deadbeef"

        # Repo persistence got the verbatim verification_type
        fake_repo.transition_to_magic_link_sent.assert_awaited_once()
        kwargs = fake_repo.transition_to_magic_link_sent.await_args.kwargs
        assert kwargs["verification_type"] == "signup"
        assert kwargs["hashed_token"] == "hash-deadbeef"
        assert kwargs["telegram_id"] == 42


# ---------------------------------------------------------------------------
# GH #435: action_link must be PKCE token_hash URL, not Supabase hosted URL.
# ---------------------------------------------------------------------------


def test_action_link_is_pkce_token_hash_url():
    """GH #435 (CRITICAL): action_link must be portal /auth/confirm PKCE URL.

    Previously the handler returned props.action_link (Supabase hosted URL
    that 302s back with tokens in the URL fragment). A server-side route
    handler (/auth/confirm) cannot read URL fragments — the user landed on
    /login?error=missing_params.

    The fix: action_link must be constructed as:
        {portal_url}/auth/confirm?token_hash={hashed_token}&type=magiclink&next=/onboarding

    Assert using urllib.parse to verify exact query params are present.
    """
    import urllib.parse
    from nikita.config.settings import get_settings

    settings = get_settings()
    service_key = "test-service-key-deadbeef"
    portal_url = settings.portal_url.rstrip("/")

    with patch.object(settings, "supabase_service_key", service_key):
        app = _build_test_app()

        fake_link_props = MagicMock()
        # props.action_link is the Supabase-hosted URL (fragment-redirect flow)
        fake_link_props.action_link = (
            "https://supabase-project.supabase.co/auth/v1/verify"
            "?token=abc123&type=magiclink"
        )
        fake_link_props.hashed_token = "pkce-hash-deadbeef"
        fake_link_props.verification_type = "magiclink"

        fake_link_result = MagicMock()
        fake_link_result.properties = fake_link_props

        fake_supabase = MagicMock()
        fake_supabase.auth.admin.generate_link = AsyncMock(
            return_value=fake_link_result
        )

        fake_repo = AsyncMock()
        fake_repo.transition_to_magic_link_sent.return_value = "row-id"

        from nikita.api.routes.portal_auth import _get_repo_for_request

        async def _override_repo():
            return fake_repo

        app.dependency_overrides[_get_repo_for_request] = _override_repo

        with patch(
            "nikita.api.routes.portal_auth.get_supabase_client",
            new=AsyncMock(return_value=fake_supabase),
        ):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
                headers={"Authorization": f"Bearer {service_key}"},
                json={"telegram_id": 99, "email": "pkce@example.com"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()

        action_link = body["action_link"]
        parsed = urllib.parse.urlparse(action_link)
        qs = urllib.parse.parse_qs(parsed.query)

        # Must be the portal's /auth/confirm route, not the Supabase hosted URL
        assert parsed.scheme in ("http", "https"), f"unexpected scheme in {action_link}"
        assert parsed.path == "/auth/confirm", (
            f"action_link path must be /auth/confirm, got {parsed.path!r}. "
            "GH #435: Supabase hosted URL causes fragment-redirect that server "
            "route handler cannot read."
        )
        assert portal_url in action_link, (
            f"action_link must point to portal ({portal_url}), got {action_link!r}"
        )
        assert qs.get("token_hash") == ["pkce-hash-deadbeef"], (
            f"action_link must carry token_hash query param for PKCE flow, "
            f"got qs={qs!r}. GH #435."
        )
        assert qs.get("type") == ["magiclink"], (
            f"action_link must carry type=magiclink query param, got qs={qs!r}"
        )
        assert qs.get("next") == ["/onboarding"], (
            f"action_link must carry next=/onboarding query param, got qs={qs!r}"
        )
