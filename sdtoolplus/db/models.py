# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sqlalchemy import Column, Integer, DateTime, Unicode
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunDB(Base):  # type: ignore
    __tablename__ = "rundb"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    status = Column(Unicode(20))
