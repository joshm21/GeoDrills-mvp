import json
import re
import os
import uuid
from jinja2 import Environment, FileSystemLoader

# --- Configuration ---
INPUT_SCHEMA = 'schema.json'
TEMPLATE_DIR = 'templates'
OUTPUT_DIR = 'dist'
REGISTRY_FILE = 'drill_registry.json'


def build():
    # 1. Load the human-readable schema
    if not os.path.exists(INPUT_SCHEMA):
        print(f"Error: {INPUT_SCHEMA} not found.")
        return

    with open(INPUT_SCHEMA, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    # Get the seed from config, fallback to a default if missing
    seed_string = schema.get("config", {}).get("uuid_seed", "default_seed")
    # Create a namespace (UUID) based on your seed string
    NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, seed_string)

    # 2. Setup Jinja2 Environment
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    # 3. Data Processing & UUID Generation
    # We create a new registry and update the schema object with the IDs
    drill_registry = {}
    nav_items = [{"title": p["title"], "url": f"{p['title']}.html"}
                 for p in schema["pages"]]

    for page in schema["pages"]:
        for section in page["sections"]:
            processed_lessons = []
            for lesson in section["lessons"]:
                # Handle both simple string lessons and object lessons
                lesson_name = lesson if isinstance(
                    lesson, str) else lesson['name']
                lesson_data = {"name": lesson_name, "levels": []}

                # Generate 3 levels with fresh UUIDs
                for i in range(1, 4):
                    # Create a unique 'name' for this specific level
                    # e.g., "Sounds|Vowels|Short A|Level 1"
                    unique_path = f"{page['title']}|{section['heading']}|{lesson_name}|{i}"
                    # Generate a stable UUID based on the namespace and the path
                    u = str(uuid.uuid5(NAMESPACE, unique_path))

                    lesson_data["levels"].append({"num": i, "uid": u})

                    # Store mapping for the API registry
                    drill_registry[u] = [
                        page['title'],
                        section['heading'],
                        lesson_name,
                        i
                    ]
                processed_lessons.append(lesson_data)

            # Replace the simple string list with our enriched object list
            section["lessons"] = processed_lessons

    # 4. Create Output Directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 5. Render Static Selection Pages (Sounds, Verbs, etc.)
    list_template = env.get_template('list.j2')
    for page in schema["pages"]:
        output_path = os.path.join(OUTPUT_DIR, f"{page['title']}.html")
        rendered_html = list_template.render(
            page=page,
            nav_items=nav_items,
            config=schema.get("config", {})
        )
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(rendered_html)

    # 6. Render the App Page (The Vue frontend)
    app_template = env.get_template('app.j2')
    app_output_path = os.path.join(OUTPUT_DIR, "App.html")
    rendered_app = app_template.render(
        page={"title": "Drill"},  # Dummy page object for the nav active state
        nav_items=nav_items,
        config=schema.get("config", {})
    )
    with open(app_output_path, "w", encoding='utf-8') as f:
        f.write(rendered_app)

    # 7. Render Index/Landing Page
    index_template = env.get_template('index.j2')
    index_output_path = os.path.join(OUTPUT_DIR, "index.html")
    rendered_index = index_template.render(
        page={"title": "Home"},
        nav_items=nav_items,
        config=schema.get("config", {})
    )
    with open(index_output_path, "w", encoding='utf-8') as f:
        f.write(rendered_index)

    # 8. Save the Registry for your API
    json_string = json.dumps(drill_registry, indent=2, ensure_ascii=False)
    json_string = re.sub(r'\[\s+([^\]]+?)\s+\]',
                         lambda m: "[" +
                         re.sub(r'\s*\n\s*', ' ', m.group(1)) + "]",
                         json_string)  # collapse lists into a single line
    with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
        f.write(json_string)

    print(f"✅ Success!")
    print(f"   - {len(drill_registry)} fresh UUIDs generated.")
    print(f"   - Registry saved to {REGISTRY_FILE} (Upload this to your API).")
    print(f"   - HTML files generated in /{OUTPUT_DIR}")


if __name__ == "__main__":
    build()
