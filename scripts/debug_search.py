from ddgs import DDGS

def debug_signal(company, query_suffix):
    print(f"\n--- SIGNAL SEARCH: {company} + {query_suffix} ---")
    try:
        results = DDGS().text(f'"{company}" {query_suffix}', max_results=3)
        if not results:
            print("NO RESULTS")
        else:
            for res in results:
                print(f"- {res.get('title')} ({res.get('href')})")
                print(f"  Snippet: {res.get('body')[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_signal("ViaDirect", "hiring OR jobs")
    debug_signal("Abuzz", "new project OR contract")
    debug_signal("Mappedin", "investment OR funding")


