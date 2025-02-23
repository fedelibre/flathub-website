from functools import lru_cache
from typing import Dict

import sentry_sdk
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, PlainTextResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from . import (
    apps,
    compat,
    config,
    db,
    exceptions,
    feeds,
    logins,
    picks,
    purchases,
    schemas,
    search,
    sitemap,
    stats,
    summary,
    utils,
    vending,
    verification,
    wallet,
)

app = FastAPI(title=config.settings.app_name, default_response_class=ORJSONResponse)

if config.settings.sentry_dsn:
    sentry_sdk.init(
        dsn=config.settings.sentry_dsn,
        traces_sample_rate=0.01,
        environment="production",
        integrations=[
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
    )
    app.add_middleware(SentryAsgiMiddleware)

origins = config.settings.cors_origins.split(" ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logins.register_to_app(app)
wallet.register_to_app(app)
vending.register_to_app(app)

verification.register_to_app(app)
purchases.register_to_app(app)

compat.register_to_app(app)


@app.on_event("startup")
def startup_event():
    db.wait_for_redis()

    picks.initialize()
    verification.initialize()


@app.post("/update")
def update():
    new_apps, all_app_ids = apps.load_appstream()
    summary.update()
    picks.update()
    stats.update(all_app_ids)
    verification.update()
    exceptions.update()

    if new_apps:
        new_apps_zset = {}
        for appid in new_apps:
            if metadata := db.get_json_key(f"summary:{appid}"):
                new_apps_zset[appid] = metadata.get("timestamp", 0)
        if new_apps_zset:
            db.redis_conn.zadd("new_apps_zset", new_apps_zset)

    get_recently_updated.cache_clear()
    get_recently_added.cache_clear()
    get_category.cache_clear()


@app.get("/category/{category}")
@lru_cache()
def get_category(
    category: schemas.Category,
    page: int = None,
    per_page: int = None,
    response: Response = Response,
):
    if (page is None and per_page is not None) or (
        page is not None and per_page is None
    ):
        response.status_code = 400
        return response

    ids = apps.get_category(category)

    sorted_ids = utils.sort_ids_by_installs(ids)

    if page is None:
        category = sorted_ids
    else:
        category = sorted_ids.__getitem__(slice(per_page * (page - 1), per_page * page))

    result = [utils.get_listing_app(f"apps:{appid}") for appid in category]
    return [app for app in result if app]


@app.get("/developer")
def get_developers():
    return db.get_developers()


@app.get("/developer/{developer}")
def get_developer(
    developer: str,
    response: Response,
):
    ids = apps.get_developer(developer)

    if not ids:
        response.status_code = 404
        return response

    sorted_ids = utils.sort_ids_by_installs(ids)

    result = [utils.get_listing_app(f"apps:{appid}") for appid in sorted_ids]
    return [app for app in result if app]


@app.get("/projectgroup")
def get_project_groups():
    return db.get_project_groups()


@app.get("/projectgroup/{project_group}")
def get_project_group(
    project_group: str,
    response: Response,
):
    ids = apps.get_project_group(project_group)

    if not ids:
        response.status_code = 404
        return response

    sorted_ids = utils.sort_ids_by_installs(ids)

    result = [utils.get_listing_app(f"apps:{appid}") for appid in sorted_ids]
    return [app for app in result if app]


@app.get("/appstream")
def list_appstream():
    return apps.list_appstream()


@app.get("/appstream/{appid}", status_code=200)
def get_appstream(appid: str, response: Response):
    if value := db.get_json_key(f"apps:{appid}"):
        return value

    response.status_code = 404
    return None


@app.get("/search/{userquery}")
def get_search(userquery: str):
    return search.search_apps(userquery)


@app.get("/collection/recently-updated")
@app.get("/collection/recently-updated/{limit}")
@lru_cache()
def get_recently_updated(limit: int = 100):
    recent = apps.get_recently_updated(limit)
    result = [utils.get_listing_app(f"apps:{appid}") for appid in recent]
    return [app for app in result if app]


@app.get("/collection/recently-added")
@app.get("/collection/recently-added/{limit}")
@lru_cache()
def get_recently_added(limit: int = 100):
    recent = apps.get_recently_added(limit)
    result = [utils.get_listing_app(f"apps:{appid}") for appid in recent]
    return [app for app in result if app]


@app.get("/picks/{pick}")
def get_picks(pick: str, response: Response):
    if picks_ids := picks.get_pick(pick):
        result = [utils.get_listing_app(f"apps:{appid}") for appid in picks_ids]
        return [app for app in result if app]

    response.status_code = 404


@app.get("/popular")
def get_popular(limit: int = 100):
    popular = stats.get_popular(None)[0:limit]
    result = [utils.get_listing_app(f"apps:{appid}") for appid in popular]
    return [app for app in result if app]


@app.get("/popular/{days}")
def get_popular_days(days: int):
    popular = stats.get_popular(days)
    result = [utils.get_listing_app(f"apps:{appid}") for appid in popular]
    return [app for app in result if app]


@app.get("/feed/recently-updated")
def get_recently_updated_apps_feed():
    return Response(
        content=feeds.get_recently_updated_apps_feed(), media_type="application/rss+xml"
    )


@app.get("/feed/new")
def get_new_apps_feed():
    return Response(content=feeds.get_new_apps_feed(), media_type="application/rss+xml")


@app.get("/status", status_code=200)
def healthcheck():
    return {"status": "OK"}


@app.get("/stats", status_code=200)
def get_stats(response: Response):
    if value := db.get_json_key("stats"):
        return value

    response.status_code = 404
    return None


@app.get("/stats/{appid}", status_code=200)
def get_stats_for_app(appid: str, response: Response, all=False, days: int = 180):
    if value := stats.get_installs_by_ids([appid]).get(appid, None):
        if all:
            return value

        if per_day := value.get("installs_per_day"):
            requested_dates = list(per_day.keys())[-days:]
            requested_per_day = {date: per_day[date] for date in requested_dates}
            value["installs_per_day"] = requested_per_day
            return value

    response.status_code = 404
    return None


@app.get("/summary/{appid}", status_code=200)
def get_summary(appid: str, response: Response):
    if value := db.get_json_key(f"summary:{appid}"):
        return value

    response.status_code = 404
    return None


@app.get("/platforms", status_code=200)
def get_platforms() -> Dict[str, utils.Platform]:
    """
    Return a mapping from org-name to platform aliases and dependencies which are
    recognised by the backend.  These are used by things such as the transactions
    and donations APIs to address amounts to the platforms.
    """
    return utils.PLATFORMS


@app.get("/sitemap/text", response_class=PlainTextResponse)
def get_sitemap():
    return sitemap.generate_text()


@app.get("/exceptions/{appid}")
def get_exceptions(appid: str, response: Response):
    if exc := db.get_json_key(f"exc:{appid}"):
        return exc

    response.status_code = 404
    return None
