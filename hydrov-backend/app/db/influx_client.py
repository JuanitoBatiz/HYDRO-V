# app/db/influx_client.py
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write_api_async import WriteApiAsync
from influxdb_client.client.query_api_async import QueryApiAsync
from app.core.config import settings


class InfluxManager:
    """
    Manager singleton del cliente InfluxDB async.
    Se inicializa en el lifespan de FastAPI y se cierra al apagar.
    """
    _client:    InfluxDBClientAsync | None = None
    _write_api: WriteApiAsync | None       = None
    _query_api: QueryApiAsync | None       = None

    @classmethod
    async def connect(cls) -> None:
        cls._client = InfluxDBClientAsync(
            url=settings.INFLUX_URL,
            token=settings.INFLUX_TOKEN,
            org=settings.INFLUX_ORG,
        )
        cls._write_api = cls._client.write_api()
        cls._query_api = cls._client.query_api()

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            await cls._client.close()
            cls._client    = None
            cls._write_api = None
            cls._query_api = None

    @classmethod
    def get_write_api(cls) -> WriteApiAsync:
        if not cls._write_api:
            raise RuntimeError("InfluxDB no inicializado. Llama a InfluxManager.connect() primero.")
        return cls._write_api

    @classmethod
    def get_query_api(cls) -> QueryApiAsync:
        if not cls._query_api:
            raise RuntimeError("InfluxDB no inicializado. Llama a InfluxManager.connect() primero.")
        return cls._query_api


# ── Dependency para FastAPI ───────────────────────────────────────
def get_influx_write() -> WriteApiAsync:
    """
    Uso en endpoints:

        from app.db.influx_client import get_influx_write

        async def my_endpoint(write_api = Depends(get_influx_write)):
            ...
    """
    return InfluxManager.get_write_api()


def get_influx_query() -> QueryApiAsync:
    return InfluxManager.get_query_api()