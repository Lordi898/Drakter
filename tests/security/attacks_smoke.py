"""Comprueba que el propio banco distingue un acceso legítimo de uno rechazado."""

from redlib import Context, attack, expect


@attack("SMOKE-01", "El token legítimo entra y sin token no", guarantee="Control del banco")
def legitimate_access(ctx: Context) -> None:
    expect(ctx.http("GET", ctx.route("auth_check")).status == 200, "token legítimo rechazado")
    expect(ctx.http("GET", ctx.route("auth_check"), token=False).status == 401, "entra sin token")
