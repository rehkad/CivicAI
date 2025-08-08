from __future__ import annotations

import os
from typing import Any, Dict, List
import httpx


def _safe_get(d: Dict[str, Any], *keys: str, default: str = "") -> str:
    cur: Any = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur if isinstance(cur, str) else default


async def search_federal_register(query: str, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://www.federalregister.gov/api/v1/documents.json"
    params = {
        "per_page": str(limit),
        "order": "relevance",
        "conditions[term]": query,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    items = []
    for doc in data.get("results", [])[:limit]:
        items.append(
            {
                "source": "federal_register",
                "title": _safe_get(doc, "title"),
                "url": _safe_get(doc, "html_url"),
                "snippet": _safe_get(doc, "abstract"),
            }
        )
    return items


async def search_regulations_gov(query: str, limit: int = 5) -> List[Dict[str, str]]:
    api_key = os.getenv("REGULATIONS_API_KEY")
    if not api_key:
        return []
    url = "https://api.regulations.gov/v4/documents"
    params = {"filter": f"searchTerm:{query}", "page[size]": str(limit)}
    headers = {"X-Api-Key": api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    items = []
    for doc in data.get("data", [])[:limit]:
        attrs = doc.get("attributes", {})
        items.append(
            {
                "source": "regulations_gov",
                "title": attrs.get("title", ""),
                "url": attrs.get("documentHtmlUrl", "") or attrs.get("documentUrl", ""),
                "snippet": attrs.get("abstract", ""),
            }
        )
    return items


async def search_govinfo(query: str, limit: int = 5) -> List[Dict[str, str]]:
    api_key = os.getenv("GOVINFO_API_KEY")
    if not api_key:
        return []
    url = "https://api.govinfo.gov/search"
    params = {"query": query, "pageSize": str(limit), "api_key": api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    items = []
    for result in data.get("results", [])[:limit]:
        items.append(
            {
                "source": "govinfo",
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("summary", ""),
            }
        )
    return items


async def socrata_search(domain: str, dataset: str, where: str | None = None, limit: int = 5) -> List[Dict[str, str]]:
    token = os.getenv("SOCRATA_APP_TOKEN")
    url = f"https://{domain}/resource/{dataset}.json"
    params = {"$limit": str(limit)}
    if where:
        params["$where"] = where
    headers = {"X-App-Token": token} if token else {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    # Convert rows into simple string snippets
    items: List[Dict[str, str]] = []
    for row in data[:limit]:
        snippet = "; ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
        items.append({"source": "socrata", "title": f"{domain}/{dataset}", "url": url, "snippet": snippet})
    return items


async def arcgis_query(service_url: str, where: str | None = None, out_fields: str | None = None, limit: int = 5) -> List[Dict[str, str]]:
    url = service_url.rstrip("/")
    params = {
        "f": "json",
        "where": where or "1=1",
        "outFields": out_fields or "*",
        "resultRecordCount": str(limit),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    items: List[Dict[str, str]] = []
    for feat in data.get("features", [])[:limit]:
        attrs = feat.get("attributes", {})
        snippet = "; ".join(f"{k}: {v}" for k, v in list(attrs.items())[:6])
        items.append({"source": "arcgis", "title": attrs.get("NAME", "ArcGIS Feature"), "url": service_url, "snippet": snippet})
    return items


async def search_datagov(query: str, limit: int = 5) -> List[Dict[str, str]]:
    # data.gov catalog via CKAN
    url = "https://catalog.data.gov/api/3/action/package_search"
    params = {"q": query, "rows": str(limit)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    results = data.get("result", {}).get("results", [])
    items: List[Dict[str, str]] = []
    for pkg in results[:limit]:
        items.append(
            {
                "source": "data_gov",
                "title": pkg.get("title", ""),
                "url": f"https://catalog.data.gov/dataset/{pkg.get('name','')}",
                "snippet": pkg.get("notes", ""),
            }
        )
    return items


async def search_census_acs(query: str, limit: int = 5) -> List[Dict[str, str]]:
    # Placeholder: The ACS API is parameterized by dataset and variables.
    # For now, return empty to avoid misleading results without specific vars.
    return []


async def search_usaspending(query: str, limit: int = 5) -> List[Dict[str, str]]:
    # USAspending advanced search requires complex POST; skip for now with empty stub
    return []


async def census_acs(dataset: str, year: int, variables: List[str], for_geo: str, in_geo: str | None = None, limit: int = 5) -> List[Dict[str, str]]:
    base = f"https://api.census.gov/data/{year}/{dataset}"
    get_vars = ",".join(["NAME"] + variables[:24])  # API limit on vars per request
    params = {
        "get": get_vars,
        "for": for_geo,
    }
    if in_geo:
        params["in"] = in_geo
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(base, params=params)
        r.raise_for_status()
        data = r.json()
    items: List[Dict[str, str]] = []
    if not data or len(data) < 2:
        return items
    headers = data[0]
    for row in data[1:limit+1]:
        obj = dict(zip(headers, row))
        snippet = "; ".join(f"{k}: {obj[k]}" for k in headers if k != "NAME")
        items.append({
            "source": "census_acs",
            "title": obj.get("NAME", "Census ACS"),
            "url": r.request.url.__str__(),
            "snippet": snippet,
        })
    return items


async def usaspending_search(query: str, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    payload = {
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Action Date"],
        "filters": {"keywords": [query]},
        "page": 1,
        "limit": limit,
        "sort": "Award Amount",
        "order": "desc",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    items: List[Dict[str, str]] = []
    for res in data.get("results", [])[:limit]:
        title = f"{res.get('Recipient Name','Unknown')} - ${res.get('Award Amount','?')}"
        link_id = res.get("Generated Unique Award ID") or res.get("generated_unique_award_id")
        link = f"https://www.usaspending.gov/award/{link_id}" if link_id else ""
        items.append({
            "source": "usaspending",
            "title": title,
            "url": link,
            "snippet": f"Award ID: {res.get('Award ID','')}; Action Date: {res.get('Action Date','')}",
        })
    return items


