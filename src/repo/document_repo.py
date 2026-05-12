from sqlmodel import select
from src.model import Document


class DocumentRepo:
    def __init__(self, session):
        self.session = session

    async def create(self, doc: Document):
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get_by_hash_and_user(self, file_hash: str, user_id: int):
        result = await self.session.exec(
            select(Document)
            .where(Document.file_hash == file_hash)
            .where(Document.user_id == user_id)
        )
        return result.first()

    async def get_by_user(self, user_id: int, offset=0, limit=10):
        result = await self.session.exec(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return result.all()

    async def count_by_user(self, user_id: int):
        result = await self.session.exec(
            select(Document).where(Document.user_id == user_id)
        )
        return len(result.all())

    async def get_by_id(self, doc_id: int):
        result = await self.session.exec(
            select(Document).where(Document.id == doc_id)
        )
        return result.first()

    async def delete(self, doc: Document):
        await self.session.delete(doc)
        await self.session.commit()