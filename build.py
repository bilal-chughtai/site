from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, Template
import yaml
import os
from datetime import datetime
import markdown
from markdown.extensions import fenced_code, tables
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import re
import shutil
from bs4 import BeautifulSoup
from itertools import groupby
from operator import attrgetter
from urllib.parse import urlparse
import uuid
import xml.etree.ElementTree as ET
from typing import Any

from latex_wrangle import LatexExtension

# External links configuration
EXTERNAL_LINKS = {
    "strava": "https://www.strava.com/athletes/32291390",
    "github": "https://github.com/bilal-chughtai",
    "linkedin": "https://www.linkedin.com/in/bilalchughtai/",
    "lesswrong": "https://www.lesswrong.com/users/bilalchughtai",
    "twitter": "https://x.com/bilalchughtai_",
    "instapaper": "https://www.instapaper.com/p/bilalchughtai",
    "scholar": "https://scholar.google.com/citations?user=i-L98bwAAAAJ&hl=en",
    "email": "mailto:brchughtaii@gmail.com",
    "hd-streamlit": "https://bilals-health-dashboard-personal.streamlit.app/",
}


class FootnoteDataAttributeExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(
            FootnoteDataAttributeProcessor(md), "footnote_data_attr", 5
        )


class FootnoteDataAttributeProcessor(Treeprocessor):
    def run(self, root):
        # Find all anchor tags that are footnote references and capture HTML
        for ref in root.findall('.//a[@class="footnote-ref"]'):
            href = ref.get("href", "")
            if href.startswith("#fn:"):
                footnote_id = href[4:]
                footnote = root.find(
                    f'.//div[@class="footnote"]//li[@id="fn:{footnote_id}"]'
                )
                if footnote is not None:
                    # Serialize footnote li HTML and extract inner contents
                    raw_html = ET.tostring(footnote, encoding="unicode", method="html")
                    soup = BeautifulSoup(raw_html, "html.parser")
                    # inner HTML of the <li>
                    inner_html = "".join(str(child) for child in soup.li.contents)
                    # Attach the HTML as a data attribute
                    ref.set("data-footnote", inner_html)
        return root


@dataclass
class PostMeta:
    label: str
    title: str
    date: datetime
    description: str  # abstract that shows up at the top of the post
    math: bool  # whether latex is included
    tags: list[str]  # a list of tags, e.g. ["computing", "civilisation"]
    type: list[str] | None = (
        None  # a hierarchical list of subtypes, e.g. ["book reviews", "fiction"]
    )
    sublist: list[str] | None = (
        None  # for short review posts, a list of books reviewed, to list on main page
    )
    coauthors: list[str] | None = None  # a list of coauthors
    prequel: str | None = None  # label of the post that is the prequel to this one
    sequel: str | None = None  # label of the post that is the sequel to this one
    elsewhere: list[str] | None = (
        None  # a list of links to other places where this post has been published
    )
    word_count: int | None = None  # Word count of the post content
    draft: bool = False  # whether this post is a draft (hidden from landing page)


@dataclass
class Post:
    meta: PostMeta
    content: str


def default_post_url(label: str) -> str:
    return f"{label}/"


def load_metas(path: str = "src/meta.yaml") -> list[PostMeta]:
    with open(path, "r") as f:
        raw_metas = yaml.load(f, Loader=yaml.FullLoader)
    return [PostMeta(**meta) for meta in raw_metas]


def load_posts(path: str = "src") -> list[Post]:
    try:
        metas = load_metas()
    except FileNotFoundError:
        print(f"Error: Meta file not found.")
        return []
    except yaml.YAMLError:
        print(f"Error: Invalid YAML in meta file.")
        return []

    posts = []
    for meta in metas:
        try:
            with open(f"{path}/{meta.label}.md", "r") as f:
                content = f.read()
            posts.append(Post(meta, content))
        except FileNotFoundError:
            print(
                f"Warning: Source file for '{meta.label}' not found, searched at '{path}/{meta.label}.md'. Skipping."
            )
        except IOError as e:
            print(f"Error reading file for '{meta.label}': {str(e)}. Skipping.")

    return posts


def collect_images(content):
    """Extract image references from markdown content."""
    image_pattern = r"!\[.*?\]\((.*?)\)"
    return re.findall(image_pattern, content)


def copy_images(post, images, out_dir):
    """Copy images to post-specific asset folder and update references."""
    post_assets_dir = os.path.join(out_dir, post.meta.label, "assets")
    os.makedirs(post_assets_dir, exist_ok=True)

    for img_path in images:
        src_path = os.path.join("src", img_path)
        dst_path = os.path.join(post_assets_dir, os.path.basename(img_path))
        shutil.copy2(src_path, dst_path)

        # Update image reference in content
        relative_path = os.path.join("assets", os.path.basename(img_path))
        post.content = post.content.replace(img_path, relative_path)


def process_images(posts, out_dir):
    """Process images for all posts."""
    for post in posts:
        images = collect_images(post.content)
        copy_images(post, images, out_dir)


def generate_toc(html_content: str, include_h1: bool = True):
    soup = BeautifulSoup(html_content, "html.parser")
    headers = soup.find_all(
        (["h1"] if include_h1 else []) + ["h2", "h3", "h4", "h5", "h6"]
    )
    toc = []
    for i, header in enumerate(headers):
        header_id = f"section-{i}"
        header["id"] = header_id
        toc.append({"level": int(header.name[1]), "text": header.text, "id": header_id})
    return toc, str(soup)


def remove_first_h1(markdown_content):
    """Remove the first top-level heading if it's at the start of the content."""
    lines = markdown_content.split("\n")
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return markdown_content


def add_br_before_footnotes(html_content):
    """Add a <br> tag before the footnotes section."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the footnote div
    footnote_div = soup.find("div", class_="footnote")
    if footnote_div:
        # Find the <ol> element inside footnote
        ol_element = footnote_div.find("ol")
        if ol_element:
            # Create a <br> element
            br_tag = soup.new_tag("br")
            # Insert the <br> before the <ol> element
            ol_element.insert_before(br_tag)

    return str(soup)


def format_date_with_ordinal(date_obj):
    """Format date with ordinal suffix (1st, 2nd, 3rd, etc.)"""
    day = date_obj.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}[day % 10]

    return date_obj.strftime(f"%-d{suffix} %B %Y")


def generate_html(
    posts: list[Post], templates_dir: str = "templates", out_dir: str = "out"
):
    jinja_env = Environment(loader=FileSystemLoader(templates_dir))
    jinja_env.filters["format_date"] = format_date_with_ordinal

    process_images(posts, out_dir)
    context = prepare_common_context()
    sorted_posts = create_post_groupings(posts)

    generate_main_page(jinja_env, sorted_posts, context, out_dir)

    for post in posts:
        generate_post_page(jinja_env, post, context, out_dir, posts)


def generate_post_page(
    env: Environment, post: Post, context: dict, out_dir: str, posts: list[Post]
):
    post_template = env.get_template("post.html")

    extensions, latex_ext = get_markdown_extensions(post.meta)
    md = markdown.Markdown(extensions=extensions)

    post_content = prepare_post_content(post, md)
    toc, post_content_html = generate_toc(post_content)

    post_html = render_post_content(
        post_template, post, post_content_html, toc, context, posts
    )

    if post.meta.math and latex_ext:
        post_html = latex_ext.restore_latex(post_html)

    post_dir = os.path.join(out_dir, post.meta.label)
    os.makedirs(post_dir, exist_ok=True)
    write_to_file(os.path.join(post_dir, "index.html"), post_html)


def prepare_common_context():
    return {
        "pages": [{"url": "index.html", "title": "Home"}],
        "current_year": datetime.now().year,
        "author_name": "Your Name",  # Replace with your actual name or make this configurable
    }


@dataclass
class PostGroupings:
    posts_by_year: list[dict[str, list[Post]]]
    posts_by_tag: list[dict[str, list[Post]]]


def create_post_groupings(posts: list[Post]) -> PostGroupings:
    # Filter out draft posts from landing page
    published_posts = [post for post in posts if not post.meta.draft]

    for post in published_posts:
        if len(post.meta.tags) == 0:
            post.meta.tags = ["[untagged]"]

    sorted_posts = sorted(published_posts, key=lambda x: x.meta.date, reverse=True)

    posts_by_year = []
    for year, year_posts in groupby(sorted_posts, key=lambda x: x.meta.date.year):
        posts_by_year.append({"year": year, "posts": list(year_posts)})

    # posts may have many tags!
    posts_by_tag = []
    tags = set()
    for post in published_posts:
        for tag in post.meta.tags:
            tags.add(tag)
    for tag in tags:
        posts_by_tag.append(
            {
                "tag": tag,
                "posts": sorted(
                    [post for post in published_posts if tag in post.meta.tags],
                    key=lambda x: x.meta.date,
                    reverse=True,
                ),
            }
        )
    posts_by_tag.sort(key=lambda tag_di: len(tag_di["posts"]), reverse=True)

    return PostGroupings(posts_by_year, posts_by_tag)


def generate_main_page(
    jinja_env: Environment, post_groupings: PostGroupings, context: dict, out_dir: str
):
    main_template = jinja_env.get_template("main.html")
    main_content = render_main_content(
        main_template, post_groupings.posts_by_year, context
    )

    write_to_file(os.path.join(out_dir, "index.html"), main_content)

    toc, main_content = generate_toc(main_content, include_h1=False)
    main_html = render_main_content_with_toc(
        main_template, post_groupings, context, toc
    )

    write_to_file(os.path.join(out_dir, "index.html"), main_html)


def render_main_content(
    jinja_template: Template, posts_by_year: list[dict[str, list[Post]]], context: dict
):
    return jinja_template.render(
        posts_by_year=posts_by_year, use_mathjax=False, is_index=True, **context
    )


def render_main_content_with_toc(
    template: Template,
    post_groupings: PostGroupings,
    context: dict,
    toc: list[dict[str, str]],
):
    return template.render(
        posts_by_year=post_groupings.posts_by_year,
        posts_by_tag=post_groupings.posts_by_tag,
        use_mathjax=False,
        is_index=True,
        toc=toc,
        **context,
    )


def prepare_post_content(post: Post, md: markdown.Markdown):
    post.content = remove_first_h1(post.content)
    post_content_html = md.convert(post.content)

    # Add <br> before footnotes
    post_content_html = add_br_before_footnotes(post_content_html)

    # Calculate word count
    word_count = len(post.content.split())
    post.meta.word_count = word_count  # Add word count to post metadata

    return post_content_html


def render_post_content(
    template: Template,
    post: Post,
    post_content_html: str,
    toc: list[dict[str, str]],
    context: dict,
    posts: list[Post],
):
    # don't include old blog in "elsewhere" category
    post.meta.elsewhere = (
        [
            link
            for link in post.meta.elsewhere
            if (
                "www.strataoftheworld.com" not in link
                and "strataoftheworld.blogspot.com" not in link
            )
        ]
        if post.meta.elsewhere
        else None
    )

    return template.render(
        post=post,
        post_content=post_content_html,
        use_mathjax=post.meta.math,
        is_index=False,
        toc=toc,
        get_post_title=lambda label: get_post_title(label, posts),
        get_domain=get_domain,
        **context,
    )


def write_to_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_css(templates_dir: str = "templates", out_dir: str = "out"):
    with open(f"{templates_dir}/style.css", "r") as f:
        css = f.read()
    if not os.path.exists(f"{out_dir}/css"):
        os.makedirs(f"{out_dir}/css")
    with open(f"{out_dir}/css/style.css", "w") as f:
        f.write(css)


def copy_favicons(src_dir: str = "src", out_dir: str = "out"):
    """Copy favicons directory to the output directory."""
    src_favicons_dir = os.path.join(src_dir, "favicons")
    dst_favicons_dir = os.path.join(out_dir, "favicons")

    if os.path.exists(src_favicons_dir):
        # Remove existing favicons directory if it exists
        if os.path.exists(dst_favicons_dir):
            shutil.rmtree(dst_favicons_dir)

        # Copy the entire favicons directory
        shutil.copytree(src_favicons_dir, dst_favicons_dir)
    else:
        print(f"Warning: Favicons directory not found: {src_favicons_dir}")


def generate_external_link_redirects(out_dir: str = "out"):
    """Generate HTML redirect pages for external links."""
    for link_name, target_url in EXTERNAL_LINKS.items():
        link_dir = os.path.join(out_dir, link_name)
        os.makedirs(link_dir, exist_ok=True)

        # Create HTML redirect page
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Redirecting to {link_name.title()}</title>
    <meta http-equiv="refresh" content="0; url={target_url}">
    <link rel="canonical" href="{target_url}">
    <script>window.location.href = "{target_url}";</script>
</head>
<body>
    <p>Redirecting to <a href="{target_url}">{link_name.title()}</a>...</p>
    <p>If you are not redirected automatically, <a href="{target_url}">click here</a>.</p>
</body>
</html>"""

        with open(os.path.join(link_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(redirect_html)


def main():
    posts = load_posts()
    generate_html(posts)
    copy_css()
    copy_favicons()
    generate_external_link_redirects()


def get_post_title(label: str, posts: list[Post]) -> str:
    for post in posts:
        if post.meta.label == label:
            return post.meta.title
    return label  # fallback to label if title not found


def get_domain(url: str) -> str:
    return urlparse(url).netloc


def get_markdown_extensions(meta: PostMeta):
    """Return a list of markdown extensions and a possible LatexExtension instance."""
    base_exts: list[Any] = [
        "fenced_code",
        "tables",
        "sane_lists",
        "footnotes",
    ]

    latex_ext: LatexExtension | None = None
    if meta.math:
        latex_ext = LatexExtension()
        base_exts.append(latex_ext)

    # Custom tree-processors (footnotes)
    base_exts.append(FootnoteDataAttributeExtension())
    return base_exts, latex_ext


if __name__ == "__main__":
    main()
