import argparse
import ast
import hashlib
import hsl
import itertools
import math
import PIL.Image
import sys


# https://docs.python.org/3/library/itertools.html#itertools-recipes
def _grouper(iterable, n, *, incomplete='fill', fillvalue=None):
    args = [iter(iterable)] * n
    if incomplete == 'fill':
        return itertools.zip_longest(*args, fillvalue=fillvalue)
    if incomplete == 'strict':
        return zip(*args, strict=True)
    if incomplete == 'ignore':
        return zip(*args)
    else:
        raise ValueError('Expected fill, strict, or ignore')


# https://processing.org/reference/map_.html
def _map_range(value: int, vmin: int, vmax: int, dmin: int, dmax: int) -> float:
    return (value - vmin) * (dmax - dmin) / (vmax - vmin + dmin)


class Identicon:

    def __init__(
            self,
            size: int = None,
            dim: int = None,
            hash: str = None,
            foreground: tuple = None,
            background: tuple = None):
        # map hex string to base10 int[] for ease of use
        # remember:
        #   - using hex splits 8-bit ints into two 4-bit chars of base 16
        #   - separating every char gives direct access to 4-bit data
        self.source = None
        self.size = 500 if size is None else size
        self.dim = 5 if dim is None else dim
        self.hash = 'md5' if hash is None else hash
        self.foreground = foreground
        self.background = (240, 240, 240) if background is None else background
        # original algorithm isn't nib efficient
        # make special case for default dim = 5
        # else optimize nib usage
        self.nibs = 32 if (self.dim == 5) else math.ceil(self.dim / 2) * self.dim

    def generate(self, input: str) -> PIL.Image.Image:
        # convert hex digest (base16) to list[int] (base10)
        # each int represents 4 bits
        slice = self._hash(input)
        self.source = list(map(lambda c: int(c, 16), slice))
        return self._image()

    # returns a slice of the resulting digest in hex
    def _hash(self, input: str) -> str:
        if self.hash == 'md5':
            result = hashlib.md5(input.encode('utf-8')).hexdigest()
        elif self.hash == 'sha256':
            result = hashlib.sha256(input.encode('utf-8')).hexdigest()
        elif self.hash == 'sha512':
            result = hashlib.sha512(input.encode('utf-8')).hexdigest()
        else:
            sys.exit(f"Error: Invalid hash algorithm."
                f"\n\t Pick from ['md5', 'sha256', 'sha512']")

        slice = result[0:self.nibs]
        if len(slice) < self.nibs:
            sys.exit(f"Error: '{self.hash}' digest too small to support "
                    f"{self.nibs / 2:.1f} bytes required to generate identicon."
                    f"\n\tSelect a larger hash or smaller identicon dimension.")
        return slice

    def _image(self) -> PIL.Image.Image:
        def rect(
                img: PIL.Image.Image,
                x0: int, y0: int, 
                x1: int, y1: int,
                color: tuple):
            for x in range(x0, x1):
                for y in range(y0, y1):
                    img.putpixel((x, y), color)

        pixel_size = int(self.size / (self.dim + 1))
        sprite_size = self.dim
        margin = int(pixel_size / 2)
        
        foreground = self._foreground()
        
        img = PIL.Image.new('RGB', (self.size, self.size), self.background)
        pixel = self._pixels()
        chunks = _grouper(pixel, sprite_size)
        for row, pix in enumerate(chunks):
            for col, painted in enumerate(pix):
                if painted:
                    x = col * pixel_size
                    y = row * pixel_size
                    rect(
                        img,
                        x + margin,
                        y + margin,
                        x + pixel_size + margin,
                        y + pixel_size + margin,
                        foreground
                    )
        return img

    def _foreground(self):
        if self.foreground is not None:
            return self.foreground

        # last 28 bits for HSL value
        h1 = self.source[self.nibs - 7] << 8
        h2 = (self.source[self.nibs - 6] << 4) | self.source[self.nibs - 5]

        h = h1 | h2
        s = (self.source[self.nibs - 4] << 4) | self.source[self.nibs - 3]
        l = (self.source[self.nibs - 2] << 4) | self.source[self.nibs - 1]
        
        hue = _map_range(h, 0, 4095, 0, 360)
        sat = _map_range(s, 0, 255, 0, 20)
        lum = _map_range(l, 0, 255, 0, 20)
        return hsl.HSL(hue, 65.0 - sat, 75.0 - lum).rgb()

    def _pixels(self) -> list[bool]:
        nibbles = iter(map(lambda x: x % 2 == 0, self.source))
        pixels = [False] * self.dim * self.dim
        half = math.ceil(self.dim / 2)
        for col in reversed(range(half)):
            for row in range(self.dim):
                ix = col + (row * self.dim)
                mirror_col = self.dim - 1 - col
                mirror_ix = mirror_col + (row * self.dim)
                paint = next(nibbles)
                pixels[ix] = paint
                pixels[mirror_ix] = paint
        return pixels

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='string to generate identicon from')

    parser.add_argument(
        '-s', '--size', 
        type=int,
        help='image size')
    parser.add_argument(
        '-d', '--dim',
        type=int,
        help='N x N dimension of the sprite')
    parser.add_argument(
        '--hash',
        type=str,
        choices=['md5', 'sha256', 'sha512'],
        help='hash algorithm to use')
    parser.add_argument(
        '-f', '--foreground',
        type=str,
        help='(R,G,B) main color')
    parser.add_argument(
        '-b', '--background',
        type=str,
        help='(R,G,B) background color')

    parser.add_argument(
        '--dont_show',
        action='store_true')
    parser.add_argument(
        '--save',
        type=str,
        help='filename to save as')
    
    args = parser.parse_args()

    if args.foreground is None:
        foreground = None
    else: foreground = ast.literal_eval(args.foreground)
    if args.background is None:
        background = None
    else: background = ast.literal_eval(args.background)

    identicon = Identicon(
        args.size,
        args.dim,
        args.hash,
        foreground,
        background
    )
    img = identicon.generate(args.input)


    if not args.dont_show:
        img.show()
    if args.save is not None:
        img.save(args.save)