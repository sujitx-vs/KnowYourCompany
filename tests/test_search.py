from tools.web_search import search_web


results = search_web("Tata Consultancy Services company overview")


for result in results:
    print("\nTITLE:", result["title"])
    print("URL:", result["url"])
    print("CONTENT:", result["content"][:500])