# Tool definitions only — no execution logic here.
# These JSON schemas are sent to Claude on every chat turn.
# Claude decides which tools to call based on user intent.

TOOL_REGISTRY: list[dict] = [
    {
        "name": "get_project_brief",
        "description": (
            "Retrieve the full structured brief for the current project. "
            "Call this when the user asks about project goals, audience, "
            "deliverables, constraints, or references."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_memory",
        "description": (
            "Store a durable fact, decision, entity, or constraint into "
            "project memory. Call this when the user confirms something "
            "important — a tech stack choice, a target platform, a key person. "
            "Do NOT store raw conversation. Store only reusable structured knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["context", "decision", "entity", "constraint"],
                    "description": (
                        "context = background facts, "
                        "decision = choices made, "
                        "entity = named things (people/tools/platforms), "
                        "constraint = hard limits"
                    ),
                },
                "key": {
                    "type": "string",
                    "description": (
                        "Short unique slug for this memory entry. "
                        "e.g. 'target_platform', 'chosen_language', 'client_name'"
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": "1-2 sentence human-readable summary of this entry.",
                },
                "detail": {
                    "type": "object",
                    "description": "Optional structured data to store alongside the summary.",
                },
            },
            "required": ["category", "key", "summary"],
        },
    },
    {
        "name": "read_memory",
        "description": (
            "Read the current project memory snapshot. "
            "Call this when you need to recall what was previously decided or established."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["context", "decision", "entity", "constraint"],
                    "description": "Filter by category. Omit to read all categories.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Generate an image from a text prompt and attach it to the project. "
            "Call this when the user asks to visualize, mock up, or illustrate something."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed image generation prompt.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "analyze_image",
        "description": (
            "Use Gemini Vision to analyze a project image and return a description. "
            "Call this when the user asks what an image shows, or wants feedback on a visual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "UUID of the project image to analyze.",
                },
            },
            "required": ["image_id"],
        },
    },
    {
        "name": "list_project_images",
        "description": (
            "List all images attached to this project with their IDs and prompts. "
            "Call this when the user asks about existing project images."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]