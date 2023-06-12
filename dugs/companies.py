from typing import Dict, List, Optional

import disnake
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from dugs.database import Company, Member


class Companies:
    """Handles caching the created companies"""

    def __init__(self, session: async_sessionmaker[AsyncSession]):
        self.session = session
        self._cache: dict[int, Dict[int, Company]] = {}
        self._at_war: dict[int, List[Optional[Company]]] = {}

    async def get_guild_companies(self, guild_id: int) -> List[Company]:
        companies = self._cache.get(guild_id, {}).values()
        if not companies:
            session = self.session()
            async with session.begin() as trans:
                result = await session.execute(
                    select(Company)
                    .where(Company.guild_id == guild_id)
                    .options(subqueryload(Company.members), subqueryload(Company.opponent))
                )
                companies = result.scalars().all()

            if not companies:
                return []

        self._cache[guild_id] = {c.id: c for c in companies}
        return companies

    async def get_companies_at_war(self, guild_id: int) -> List[Company]:
        companies = self._cache.get(guild_id, [])
        added_companies = set()

        if not companies:
            session = self.session()
            async with session.begin() as trans:
                result = await session.execute(
                    select(Company)
                    .where(Company.guild_id == guild_id, Company.at_war is True)
                    .options(subqueryload(Company.members), subqueryload(Company.opponent))
                )
                companies = result.scalars().all()

            if not companies:
                return

            for c in companies:
                if c.guild_id not in self._at_war:
                    self._at_war[c.guild_id] = []

                if c.at_war and c.opponent_id and c.opponent_id not in added_companies:
                    self._at_war[guild_id].append(c)
                    added_companies.add(c.opponent_id)

        return self._at_war.get(guild_id, [])

    async def add_company(self, guild_id: int, company: Company) -> None:
        if guild_id not in self._cache:
            self._cache[guild_id] = {}

        self._cache[guild_id][company.id] = company

        async with self.session.begin() as session:
            session.add(company)
            await session.commit()

    async def update_company(self, guild_id: int, company: Company) -> None:
        """Adds a new company"""
        if not guild_id in self._cache:
            raise ValueError(f"Guild has not created in companies yet")

        if not self._cache[guild_id].get(company.id, None):
            raise ValueError(f"Company `{company.name}` does not exist")

        self._cache[guild_id][company.id] = company

        async with self.session.begin() as session:
            result = await self.session.execute(select(Company).where(Company.id == company.id))
            _company = result.scalar_one_or_none()

            if not _company:
                raise ValueError(f"Company `{company.name}` does not exist in the database")

            else:
                _company.at_war = company.at_war
                _company.war_expires_at = company.war_expires_at
                _company.influence = company.influence
                _company.total_influence = company.total_influence
                _company.opponent = company.opponent
                _company.opponent_id = company.opponent.id if company.opponent else None

            await session.commit()

    async def get_company(self, guild_id: int, id: int) -> Optional[Company]:
        """Attempts to get a company from the cache by it's ID"""
        company = self._cache.get(guild_id, {}).get(id)
        if not company:
            session = self.session()
            async with session.begin() as trans:
                result = await session.execute(
                    select(Company)
                    .where(Company.id == id)
                    .options(subqueryload(Company.members), subqueryload(Company.opponent))
                )
                company = result.scalar_one_or_none()

            if company is None:
                return

            self._cache[guild_id][company.id] = company

        return company

    async def get_company_named(self, guild_id: int, name: str) -> Optional[Company]:
        """Attempts to get a company from the cache by it's name"""
        companies = await self.get_guild_companies(guild_id)

        for company in companies:
            if company.name.casefold() == name.casefold():
                return company

        session = self.session()
        async with session.begin() as trans:
            result = await session.execute(
                select(Company)
                .where(Company.guild_id == guild_id, Company.name == name)
                .options(subqueryload(Company.members), subqueryload(Company.opponent))
            )
            company = result.scalar_one_or_none()

        if company is None:
            return

        self._cache[guild_id][company.id] = company
        return company

    async def get_member_company(self, guild_id: int, member: disnake.Member) -> Optional[Company]:
        companies = await self.get_guild_companies(guild_id)

        for company in companies:
            if member in company.members:
                return company

        session = self.session()
        async with session.begin() as trans:
            result = await session.execute(
                select(Company)
                .where(
                    Company.guild_id == guild_id, Company.members.any(Member.member_id == member.id)
                )
                .options(subqueryload(Company.members), subqueryload(Company.opponent))
            )
            company = result.scalar_one_or_none()

        if company is None:
            return

        self._cache[guild_id][company.id] = company
        return company

    async def remove_company_member(self, company_id: int, member_id: int) -> None:
        session = self.session()
        async with session.begin() as trans:
            result = await session.execute(
                select(Company)
                .where(Company.id == company_id)
                .options(subqueryload(Company.members), subqueryload(Company.opponent))
            )
            company = result.scalar_one_or_none()

            if company is None:
                raise ValueError(f"Company does not exist with the id {company_id}")

            for member in company.members:
                if member.member_id == member_id:
                    await session.delete(member)
                    break

            await session.refresh(company)

            if len(company.members) == 0:
                self._cache[company.guild_id].pop(company.id, None)
                await session.delete(company)

            else:
                self._cache[company.guild_id][company.id] = company

            await trans.commit()

    async def add_company_member(self, member: Member) -> None:
        session = self.session()

        async with session.begin() as trans:
            result = await session.execute(
                select(Company)
                .where(Company.id == member.company_id)
                .options(subqueryload(Company.members), subqueryload(Company.opponent))
            )
            company = result.scalar_one_or_none()

            if company is None:
                raise ValueError(f"Company does not exist with id {member.company_id}")

            session.add(member)

            await session.refresh(company)
            await trans.commit()

            self._cache[company.guild_id][company.id] = company
