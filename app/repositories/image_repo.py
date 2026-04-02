from uuid import UUID, uuid4
from pathlib import Path
from typing import Optional
from app.repositories.base import BaseRepository

BUCKET = "project-images"


class ImageRepo(BaseRepository):

    TABLE = "images"

    async def create(
        self, project_id: UUID, prompt: str, url: str, provider: str
    ) -> dict:
        res = (
            await self.db.table(self.TABLE)
            .insert({
                "project_id": str(project_id),
                "prompt": prompt,
                "url": url,
                "provider": provider,
            })
            .execute()
        )
        return res.data[0]

    async def get_by_id(self, image_id: UUID) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("id", str(image_id))
            .execute()
        )
        return res.data[0] if res.data else None

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    async def update_analysis(
        self, image_id: UUID, analysis: str
    ) -> dict:
        from datetime import datetime, timezone
        res = (
            await self.db.table(self.TABLE)
            .update({
                "analysis": analysis,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(image_id))
            .execute()
        )
        return res.data[0]

    # ─── Upload endpoint ──────────────────────────────────────────────────────

    async def upload_project_image(
        self,
        project_id: UUID,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> dict:
        """
        1. Upload *file_bytes* to the `project-images` Storage bucket.
        2. Retrieve the public URL.
        3. Insert a row into the `project_images` table.
        Returns the newly inserted row as a dict.
        """
        # Build a collision-free storage path: <project_id>/<uuid><ext>
        ext = Path(original_filename).suffix  # e.g. ".jpg"
        storage_path = f"{project_id}/{uuid4()}{ext}"

        # 1. Upload to Storage (async Supabase v2)
        await self.db.storage.from_(BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "false"},
        )

        # 2. Get the public URL — must be awaited on the async Supabase v2 client
        public_url_resp = await self.db.storage.from_(BUCKET).get_public_url(storage_path)
        # async client returns a plain string
        image_url: str = (
            public_url_resp
            if isinstance(public_url_resp, str)
            else public_url_resp["publicUrl"]
        )

        # 3. Insert DB record into the existing `images` table
        res = (
            await self.db.table("images")
            .insert({
                "project_id": str(project_id),
                "url": image_url,
                "provider": "upload",  # add 'upload' to the CHECK constraint — see note
                "prompt": None,        # no prompt for file uploads
            })
            .execute()
        )
        return res.data[0]