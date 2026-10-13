import html, re
import urllib.parse, urllib.request

def web_search(query, limit=5):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "LocalAgent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=None) as response:
            body = response.read().decode("utf-8", errors="replace")
        results=[]
        for match in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
            results.append({"title": html.unescape(re.sub("<.*?>", "", match.group(2))), "url": html.unescape(match.group(1))})
            if len(results) >= limit: break
        return {"ok": True, "query": query, "results": results}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
