import sys, os, optparse, codecs, shutil, random, glob
from os.path import isdir
from os.path import join as pjoin

import Image
import jinja2
import markdown

from yaml import load, dump
from yaml import Loader, Dumper

def pick_three(lst, real):
    lst = [i for i in lst if i <> real]
    lst = random.sample(lst, 3)
    lst.append(real)
    random.shuffle(lst)
    return lst

def randrange_special(x, y, l):
    # Hmm, provide normal distribution range with no points too close
    lst = sorted([int(random.triangular(x,y)) for i in range(0,l)])
    prev = lst[0]
    for k,v in enumerate(lst[1:]):
        if (v - 40) < prev:
            lst[k+1] = v + 40
        prev = lst[k+1]
    return lst

def parse():
    parser = optparse.OptionParser(usage='%prog [options] data-directory')
    parser.add_option('-o', '--output-dir', dest="output", default="./html")
    parser.add_option('-t', '--templates-dir', dest="templates",
                      default="templates")
    parser.add_option('-m', '--media-dir', dest="media", default="./media")
    parser.add_option('-s', '--skip-images', action='store_true',
                      dest="skip_images", default=False)
    parser.add_option('-v', '--verbose', default=False,
                      action="store_true")
    return parser.parse_args()

def main(opts, args):
    """Build US Symbols static website."""

    # Make sure paths exist
    if not args:
        raise SystemExit("Please specify the data directory to read.")
    data_dir = args[0]
    if not isdir(data_dir):
        raise SystemExit("Data directory %s does not exist." % args[0])
    if not isdir(opts.output):
        raise SystemExit("Output path %s does not exist." % opts.output)
    image_dir = pjoin(opts.output, 'images')
    if not isdir(image_dir):
        os.mkdir(image_dir)
    if not isdir(opts.templates):
        raise SystemExit("Templates path %s does not exist." % opts.templates)
    if not isdir(opts.media):
        raise SystemExit("Media directory path %s does not exist." % opts.media)
    media_dir = opts.media

    # Set up template environment
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('gensite', opts.templates), extensions=['jinja2.ext.with_'])
    env.filters['markdown'] = markdown.markdown
    env.globals['pick_three'] = pick_three
    env.globals['shuffle'] = random.shuffle
    env.globals['list'] = list
    env.globals['random'] = random
    
    # Find symbol directories
    dirs = [d for d in os.listdir(data_dir)
            if d[0] != "." and isdir(pjoin(data_dir, d))]

    # Load yaml files
    pages = []
    questions = []
    answers = []
    for d in dirs:
        yml = codecs.open(pjoin(data_dir, d, 'index.yml'),"r", "utf-8").read()
        data = load(yml, Loader=Loader)
        data['id'] = d
        data['path'] = pjoin(data_dir, d)
        for q in ['main', 'bonus']:
            questions.append(data['facts'][q]['question'])
            answers.append(data['facts'][q]['answer'])
        pages.append(data)
    pages.sort(key=lambda p:p['title'])
    # Generate random coords list
    lst = randrange_special(-20, 780, len(pages))
    random.shuffle(lst)
    lst2 = list(lst)
    random.shuffle(lst2)
    # For each page generate study page, resizing and copying images
    for i, page in enumerate(pages):
        page['rand1'] = lst[i]
        page['rand2'] = lst2[i]
        page_images = pjoin(image_dir, page['id'])
        if not isdir(page_images):
            os.mkdir(page_images)
        # Resize image to large-image (1024x768 max)
        # And thumbnail image (400x400 max)
        sizes = [('large-image', (1024, 768)),
                 ('small-image', (400, 400)),
                 ('thumb', (140, 140))]
        for (name, size) in sizes:
            orig = pjoin(page['path'], page['image'])
            outfile = os.path.splitext(orig)[0] + ".%s.jpg" % name
            if not opts.skip_images:
                im = Image.open(orig)
                im.thumbnail(size, Image.ANTIALIAS)
                im.save(outfile, "JPEG")
            page[name] = os.path.basename(outfile)
            # Copy resized images to output dir
            shutil.copyfile(outfile,
                            pjoin(page_images, page[name]))
        template = env.get_template('detail.html')
        f = codecs.open(pjoin(opts.output, "%s.html" % page['id']),
                        "w", "utf-8")

        next = pages[i+1] if i+1 < len(pages) else None
        f.write(template.render(page=page, pages=pages, next=next))
        f.close()

    # Generate index.html, matching pages, quiz pages, essay page
    # Get all templates (except detail and base)
    templates = [os.path.basename(i) for i in glob.glob(pjoin(opts.templates, "*.html"))]
    templates = list(set(templates) - set(['base.html', 'detail.html']))
    for name in templates:
        template = env.get_template(name)
        q = zip(questions, answers)
        random.shuffle(q)
        myvars = dict(title="United States Symbols", pages=list(pages),
                      questions=q,
                      answers=answers)
        f = codecs.open(pjoin(opts.output, name), "w", "utf-8")
        f.write(template.render(**myvars))
        f.close()

    media = [d for d in os.listdir(media_dir)
            if d[0] != "." and os.path.isfile(pjoin(media_dir, d))]
    # And copy media to media directory
    if not isdir(pjoin(opts.output, "media")):
            os.mkdir(pjoin(opts.output, "media"))
    for f in media:
        shutil.copyfile(pjoin(media_dir, f),
                            pjoin(opts.output, "media", f))

if __name__ == '__main__':
    options, args = parse()
    main(options, args)
