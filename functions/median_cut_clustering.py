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
import numpy as np
import time

# Blender imports
import bpy

# Module imports
from .common import *


@timed_call("Cluster Time Elapsed")
def cluster_pixels(im):
    pix_1d = get_pixels(im)
    pix_2d = get_2d_pixel_array(pix_1d, im.channels)
    new_pix_2d = np.empty(pix_2d.shape, dtype=np.float32)

    new_shape = (len(pix_2d), im.channels + 1)
    pix_2d_with_idxs = np.empty(new_shape, dtype=np.float32)
    pix_2d_with_idxs[:, :-1] = pix_2d
    pix_2d_with_idxs[:, -1:] = np.arange(len(pix_2d), dtype=np.int64).reshape((len(pix_2d), 1))

    split_into_buckets(new_pix_2d, pix_2d_with_idxs, 4, im.channels)

    new_pix_1d = new_pix_2d.reshape(len(im.pixels))
    im_dup = duplicate_image(im, im.name + "_dup", new_pix_1d)


# Adapted and improved from: https://muthu.co/reducing-the-number-of-colors-of-an-image-using-median-cut-algorithm/
def median_cut_quantize(new_img_arr, img_arr, channels):
    # when it reaches the end, color quantize
    # print("to quantize: ", len(img_arr))
    color_ave = list()
    for i in range(channels):
        color_ave.append(np.mean(img_arr[:,i]))

    ave_arr = np.empty((len(img_arr), channels), dtype=img_arr.dtype)
    ave_arr[:] = color_ave
    ind_arr = np.empty(len(img_arr), dtype=np.int64)
    for i in range(channels):
        ind_arr[:] = img_arr[:,-1] * channels + i
        np.put(new_img_arr, ind_arr, ave_arr[:,i])


def split_into_buckets(new_img_arr, img_arr, depth=4, channels=3):
    """ Use Median Cut clustering to reduce image color palette to (2^depth) colors

    Parameters:
        new_img_arr  - Empty array with the target 2d pixel array size
        new_img_arr  - Array containing original pixel data (with an extra value in each pixel list containing its target index in new_img_arr)
        depth        – Represents how many colors are needed in the power of 2 (i.e. Depth of 4 means 2^4 = 16 colors)

    Returns:
        None (the array passed to 'new_img_arr' will contain the resulting pixels)
    """

    if len(img_arr) == 0:
        return

    if depth == 0:
        median_cut_quantize(new_img_arr, img_arr, channels)
        return

    ranges = []
    for i in range(channels):
        channel_vals = img_arr[:,i]
        ranges.append(np.max(channel_vals) - np.min(channel_vals))

    space_with_highest_range = ranges.index(max(ranges))
    # print("space_with_highest_range:", space_with_highest_range)
    # sort the image pixels by color space with highest range
    img_arr = img_arr[img_arr[:,space_with_highest_range].argsort()]
    # find the median to divide the array.
    median_index = (len(img_arr) + 1) // 2
    # print("median_index:", median_index)

    #split the array into two buckets along the median
    split_into_buckets(new_img_arr, img_arr[:median_index], depth - 1, channels)
    split_into_buckets(new_img_arr, img_arr[median_index:], depth - 1, channels)
