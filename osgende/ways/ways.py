# This file is part of Osgende
# Copyright (C) 2010-15 Sarah Hoffmann
#               2012-13 Michael Spreng
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
Tables for ways
"""

from osgende.subtable import TagSubTable
from osgende.tags import TagStore
import shapely.geometry as sgeom
from geoalchemy2.shape import from_shape

class Ways(OsmosisSubTable):
    """Most basic table type to construct a simple derived table from
       the ways table. The extension to OsmosisSubTable is that
       it constructs the geometry of the way.
    """

    def __init__(self, meta, name, subset=None, change=None,
                 column_geom='geom', geom_change=None, nodestore=None):
        TagSubTable.__init__(self, meta, name, source, subset=subset,
                             change=change)
        # need a geometry column
        if isinstance(column_geom, Column):
            self.column_geom = column_geom
        else:
            self.column_geom = Column(column_geom,
                                      Geometry('GEOMETRY', srid=4326))
        self.data.append_column(self.column_geom)
        self.nodestore = nodestore

        # add an additional transform to the insert statement if the srid changes
        if source.data.c.geom.type.srid != self.column_geom.type.srid:
            params = {}
            for c in self.data.c:
                if c == self.column_geom:
                    params[c.name] = func.st_transform(bindparam(c.name),
                                                       self.column_geom.type.srid)
                else:
                    params[c.name] = bindparam(c.name)
            self.stm_insert = self.stm_insert.values(params)

    def update(self, engine):
        if self.geom_change:
            self.geom_change.add_from_select(
               select([text("'D'"), self.column_geom])
                .where(self.column_id.in_(self.src.select_delete()))
            )

        TagSubTable.update(self, engine)

        if self.geom_change:
            self.geom_change.add_from_select(
               select([text("'M'"), self.column_geom])
                .where(self.column_id.in_(self.src.select_add_modify()))


    def _process_next(self, obj):
        tags = self.transform_tags(obj['id'], TagStore(obj['tags']))

        if tags is not None:
            points = [ x for x in self.nodestore[n] for n in obj['nodes'] if n in self.nodestore ]

            prev = None
            for p in points:
                if p == prev:
                    p.x += 0.00000001
                prev = p

            # ignore ways where the node geometries are missing
            if len(points) > 1:
                tags[self.column_id.name] = obj['id']
                tags[self.column_geom.name] = from_shape(sgeom.LineString(points), srid=4326)
                self.thread.conn.execute(self.compiled_insert, tags)
