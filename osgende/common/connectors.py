# This file is part of Osgende
# Copyright (C) 2015 Sarah Hoffmann
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
Various classes that provide connections between processed tables.
"""

from sqlalchemy import String, Table, Column, select, and_, text

class TableSource:
    """ Describes a source for another table.
    """

    def __init__(self, data_table, change_table=None,
                 id_column=None):
        """ Create a new table source. `data_table` must be an SQLAlchemy table
            with the data, The optional `change_table` may either be an
            SQLAlchemy table with id and action column or it may be a string
            and a table with that name will be created using the same MetaObject
            as the data_table. If no `change table is given, then it is
            assumed that a complete wipe-out/recreation is expected on update.
        """
        self.data = data_table

        if id_column is None:
            self.id_column = self.data.c.id
        else:
            self.id_column = id_column

        if change_table is None:
            self.change = None
        elif isinstance(change_table, str):
            self.change = Table(change_table, data_table.metadata,
                                self.id_column.copy(),
                                Column('action', String(1))
                               )
        else:
            self.change = change_table

    def change_id_column(self):
        return self.change.c[self.id_column.name]

    def insert_changes(self, selstm):
        """ Return Insert statement for adding rows into the change table.
            The changes are derived from an SQL select() statement.
        """
        return self.change.insert().from_select([self.change], selstm)

    def select_all(self, subset=None):
        """ Return an SQLAlchemy select statement which will return all
            data or the part restricted by `subset` which must be a WhereClause.
        """
        stm = self.data.select()
        if subset is not None:
            stm = stm.where(subset)

        return stm

    def select_updated(self, subset=None):
        """Return an SQLAlchemy select() with all data lines that have been
           added or modified and potentially match the subset.
        """
        if self.change is None:
           return self.select_all(subset)

        where = self.id_column.in_(self.select_add_modify())
        if subset is not None:
            where = and_(subset, where)

        return self.data.select().where(where)

    def select_modify_delete(self):
        """ Return am SQLAlchemy where clause describing all objects which
            have either been modified or deleted. If no change table exists
            all objects are returned.
        """
        if self.change is None:
            return select([self.id_column])

        return select([self.change_id_column()])\
                      .where(self.change.c.action != text("'A'"))

    def select_add_modify(self):
        """ Return am SQLAlchemy where clause describing all objects which
            have either been added or modified. If no change table exists
            all objects are returned.
        """
        if self.change is None:
            return select([self.id_column])

        return (select([self.change_id_column()])
                      .where(self.change.c.action != text("'D'")))


    def select_modify(self):
        """ Return am SQLAlchemy select clause describing all ids which
            have been deleted. If no change table exists
            all objects are returned.
        """
        if self.change is None:
            return select([self.id_column])

        return (select([self.change_id_column()])
                      .where(self.change.c.action == text("'M'")))
    def select_delete(self):
        """ Return am SQLAlchemy where clause describing all objects which
            have been deleted. If no change table exists
            all objects are returned.
        """
        if self.change is None:
            return select([self.id_column])

        return (select([self.change_id_column()])
                      .where(self.change.c.action == text("'D'")))
