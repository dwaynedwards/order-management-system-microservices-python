"""
Module that provides the session access to DB
"""

import contextlib
from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orders_service.exceptions import OrdersApiError, OrderServiceError
from orders_service.models import Base


class SessionManager:
    """Order API Session Manager"""

    engine: AsyncEngine | None
    sessionmaker: async_sessionmaker[AsyncSession] | None

    def initialize(self, db_url: str):
        """Initialize Session"""

        self.engine = create_async_engine(db_url)
        self.sessionmaker = async_sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    async def end(self):
        """Ends Session"""
        if self.engine is None:
            raise OrderServiceError

        await self.engine.dispose()

        self.engine = None
        self.sessionmaker = None

    @contextlib.asynccontextmanager
    async def begin(self) -> AsyncIterator[AsyncConnection]:
        """Begins Session"""

        if self.engine is None:
            raise OrderServiceError

        async with self.engine.begin() as conn:
            try:
                yield conn
            except SQLAlchemyError as e:
                await conn.rollback()
                raise OrderServiceError from e

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Handles Session"""

        if not self.sessionmaker:
            raise OrderServiceError

        session = self.sessionmaker()

        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise OrderServiceError from e
        except OrdersApiError as e:
            print("ROLLBACK!!!!!", e)
            await session.rollback()
            raise e
        finally:
            await session.close()


__session_manager: SessionManager = SessionManager()


def init_session_manager(db_url: str):
    """Initialize Session Manager"""
    __session_manager.initialize(db_url)


async def begin_session_create_tables():
    """Begins Session and creates tables"""
    async with __session_manager.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def end_session():
    """Ends Session"""
    await __session_manager.end()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Gets Session"""

    async with __session_manager.session() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
