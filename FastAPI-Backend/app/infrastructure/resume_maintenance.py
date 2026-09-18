"""Explicit owner-scoped retention maintenance; dry-run is the default."""
import argparse
import asyncio
from app.infrastructure.resume_runtime import session_factory, asset_store
from app.infrastructure.private_resume_assets import cleanup_documents
from app.infrastructure.experience_import_cleanup import cleanup_imports


async def main(owner, apply=False, max_pages=1):
    if not 0 < owner <= 2147483647 or not 1 <= max_pages <= 100:
        raise ValueError("positive owner and max-pages 1..100 required")
    factory, store = session_factory(), asset_store()
    async with factory() as session:
        document_count, import_count = 0, 0
        after = None
        for _ in range(max_pages):
            documents = await cleanup_documents(session, store, owner, dry_run=not apply, after=after)
            document_count += len(documents["document_ids"])
            if not documents["has_more"]:
                break
            after = documents["next_cursor"]
        after = None
        for _ in range(max_pages):
            imports = await cleanup_imports(session, store, owner, dry_run=not apply, after=after)
            import_count += len(imports["import_ids"])
            if not imports["has_more"]:
                break
            after = imports["next_cursor"]
        # Counts only: avoid publishing private asset names or source content in logs.
        print({"dry_run": not apply, "document_candidates": document_count,
            "import_candidates": import_count,
            "has_more": documents["has_more"] or imports["has_more"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-pages", type=int, default=1)
    options = parser.parse_args()
    asyncio.run(main(options.owner, options.apply, options.max_pages))
