"""
T054 — cached(): cache-hit no invoca al loader; cache-miss lo invoca y persiste
con el TTL correcto; comportamiento fail-open si Redis lanza una excepcion.
"""
from app.cache.analytics_cache import cached


def test_cache_hit_no_invoca_al_loader(fake_redis):
    fake_redis.set("k1", "42", ex=600)
    loader_calls = []

    def loader():
        loader_calls.append(1)
        return 999

    result = cached("k1", 600, loader)

    assert result == 42
    assert loader_calls == []  # el loader NUNCA se llamo (I de F.I.R.S.T. + fail no aplica)


def test_cache_miss_invoca_loader_y_persiste_con_ttl(fake_redis):
    loader_calls = []

    def loader():
        loader_calls.append(1)
        return {"total_users": 100}

    result = cached("k2", 123, loader)

    assert result == {"total_users": 100}
    assert loader_calls == [1]

    stored_value, expires_at = fake_redis._store["k2"]
    assert expires_at is not None


def test_fail_open_si_redis_lanza_excepcion(fake_redis):
    fake_redis.raise_on_call = True
    loader_calls = []

    def loader():
        loader_calls.append(1)
        return "valor-directo-de-postgres"

    result = cached("k3", 600, loader)

    # Fail-open: a pesar de que Redis explota, el resultado se sirve igual
    # ejecutando el loader directamente (research.md §4).
    assert result == "valor-directo-de-postgres"
    assert loader_calls == [1]
