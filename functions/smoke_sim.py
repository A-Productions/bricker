# Copyright (C) 2019 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
import time

# Module imports
from .common import *
from .general import *

# code adapted from https://github.com/bwrsandman/blender-addons/blob/master/render_povray/render.py
def get_smoke_info(source):
    if not source.smoke_data:
        return [None] * 6

    smoke_data = json.loads(decompress_str(source.smoke_data))

    # get channel data
    density_grid = smoke_data["density_grid"]
    flame_grid = smoke_data["flame_grid"]
    color_grid = smoke_data["color_grid"]
    # get resolution
    domain_res = get_adjusted_res(smoke_data, smoke_data["domain_resolution"])
    adapt = smoke_data["use_adaptive_domain"]
    max_res_i = smoke_data["resolution_max"]
    max_res = Vector(domain_res) * (max_res_i / max(domain_res))
    max_res = get_adjusted_res(smoke_data, max_res)

    return density_grid, flame_grid, color_grid, domain_res, max_res, adapt


def get_adjusted_res(smoke_data, smoke_res):
    if smoke_data["use_high_resolution"]:
        smoke_res = [int((smoke_data["amplify"] + 1) * i) for i in smoke_res]
    return smoke_res
