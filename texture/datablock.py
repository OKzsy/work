"""
# @Time    : 2019/8/21 14:19
# @Author  : zhaoss
# @FileName: datablock.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""
import sys

class DataBlock():
    """用于根据输入的影像基本信息进行影像分块"""
    def __init__(self, xsize, ysize, linesInblock=300, overlap_line=0):
        """初始化分块的基本属性"""
        self.rasterXSize = xsize
        self.rasterYSize = ysize
        self.linesblock = linesInblock
        # 计算需要分割为多少块
        residue = ysize % linesInblock
        if residue == 0:
            self.numsblocks = ysize // linesInblock
        else:
            self.numsblocks = (ysize // linesInblock) + 1
        self.overlap = overlap_line

    def block(self, IDblock):
        """对于指定的块返回该块在影像中的行列范围"""
        # 根据数据块顺序计算该块的起始 - 结尾行号
        # IDblock = IDblock - 1
        # 需要特别处理最后一块，因此判断是否该进程处理的是最后一块
        # if IDblock == totalblocknum - 1:
        if self.linesblock < self.overlap:
            sys.exit("The overlap line can't less than the lines in per block!")
        if IDblock == 0:
            # 判断块的行数是否大于总行数
            if self.linesblock >= self.rasterYSize:
                block_lines = self.rasterYSize - self.overlap
            else:
                block_lines = self.linesblock
            # 该块的起始行号
            xs_col = 0
            ys_line = 0
            rows = block_lines + self.overlap
            columns = self.rasterXSize
            tile_get = [xs_col, ys_line, columns, rows]
            ye_line = self.overlap > 0 and -self.overlap or rows
            tile_put = [0, ye_line, xs_col, ys_line]
            return tile_get, tile_put
        elif IDblock == self.numsblocks - 1:
            # 该块的起始行列号
            xs_col = 0
            ys_line = IDblock * self.linesblock - self.overlap
            rows = self.rasterYSize - IDblock * self.linesblock + self.overlap
            columns = self.rasterXSize
            tile_get = [xs_col, ys_line, columns, rows]
            tile_put = [self.overlap, rows, xs_col, ys_line + self.overlap]
            return tile_get, tile_put
        else:
            # 该块的起始行列号
            xs_col = 0
            ys_line = IDblock * self.linesblock - self.overlap
            rows = self.linesblock + self.overlap * 2
            columns = self.rasterXSize
            tile_get = [xs_col, ys_line, columns, rows]
            ye_line = self.overlap > 0 and -self.overlap or rows
            tile_put = [self.overlap, ye_line, xs_col, ys_line + self.overlap]
            return tile_get, tile_put



