from sqlmodel import select
from src.model import User


class UserRepo:
    def __init__(self, session):
        self.session = session

    async def create_user(self, user: User):
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_users(self):
        result = await self.session.exec(select(User))
        users = result.all()
    
        return users
    
    async def get_user_by_email(self, email: str):
        result = await self.session.exec(select(User).where(User.email == email))
        return result.first()