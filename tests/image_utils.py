import re
import subprocess

convert_line_regexp = re.compile('(\d+):\s+\(\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)')
def get_images_likelihood(image1, image2):

    compare = subprocess.run(['compare', image1, image2, '-compose', 'src', 'miff:-'], stdout=subprocess.PIPE, universal_newlines=True)

    convert = subprocess.run(['convert', '-', '-depth', '8', '-define', 'histogram:unique-colors=true', '-format', '%[width] %[height]\n%c', 'histogram:info:-'], stdin=compare.stdout, stdout=subprocess.PIPE, universal_newlines=True)

    compare.stdout.close()

    output = convert.communicate()[0]

    lines = output.split('\n')

    width, height = lines[0].split()

    pixels = int(width) * int(height)
    pixel_count = 0

    non_black_pixels = 0

    for i in range(1, len(lines)):
        matches = convert_line_regexp.search(lines[i])
        if matches is None:
            continue

        line_pixel = int(matches.group(1))
        pixel_count += line_pixel

        r, g, b, a = matches.group(2), matches.group(3), matches.group(4), matches.group(5)

        if int(r) == int(g) and int(g) == int(b) and ( int(b) == 255 or int(b) == int(a) ):
            # Black or grey, continue
            continue

        non_black_pixels += line_pixel

        if pixel_count == pixels:
            break

    return 1 - non_black_pixels / pixels
